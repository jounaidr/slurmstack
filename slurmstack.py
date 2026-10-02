#!/usr/bin/env python3
"""
SlurmStack Provisioner & Orchestrator
Automates parallel OpenStack VM provisioning and Slurm cluster deployment via Ansible.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import secrets

from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from util.openstack_client import OStack

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

PLAYBOOK = "playbooks/deploy_nodes.yml"


def main() -> None:
    load_dotenv()
    parser, args = parse_args()

    if args.destroy:
        destroy_cluster(args)
    else:
        validate_provision_args(args, parser)
        provision_cluster(args)


def parse_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """Parse CLI arguments, use environment variables if not present."""
    env = os.environ.get

    parser = argparse.ArgumentParser(
        description="Provision a Slurm cluster on OpenStack and deploy it with Ansible."
    )

    parser.add_argument(
        "--destroy", action="store_true", help="Tear down all cluster VMs"
    )

    # Required for both provision and destroy
    parser.add_argument(
        "-clu",
        "--cluster-name",
        default=env("SS_CLUSTER_NAME"),
        required=not env("SS_CLUSTER_NAME"),
    )
    parser.add_argument(
        "-con",
        "--controller-name",
        default=env("SS_CONTROLLER_NAME"),
        required=not env("SS_CONTROLLER_NAME"),
    )
    parser.add_argument(
        "-np",
        "--nodes-prefix",
        default=env("SS_NODES_PREFIX"),
        required=not env("SS_NODES_PREFIX"),
    )
    parser.add_argument(
        "-nc",
        "--nodes-count",
        type=int,
        default=int(env("SS_NODES_COUNT")) if env("SS_NODES_COUNT") else None,
        required=not env("SS_NODES_COUNT"),
    )
    parser.add_argument(
        "-k",
        "--ansible-key",
        default=env("SS_ANSIBLE_KEY"),
        required=not env("SS_CONTROLLER_NAME"),
    )

    # Provision only
    env_sg = env("SS_SECGROUP") or ""
    parser.add_argument("-i", "--image", default=env("SS_IMAGE"))
    parser.add_argument("-net", "--network", default=env("SS_NETWORK"))
    parser.add_argument(
        "-s", "--secgroup", nargs="+", default=env_sg.split(",") if env_sg else None
    )
    parser.add_argument(
        "-cf", "--controller-flavour", default=env("SS_CONTROLLER_FLAVOUR")
    )
    parser.add_argument("-nf", "--nodes-flavour", default=env("SS_NODES_FLAVOUR"))
    parser.add_argument("-cr", "--cluster-ip-range", default=env("SS_CLUSTER_IP_RANGE"))
    parser.add_argument("-mp", "--mariadb-pass", default=env("SS_MARIADB_PASS"))

    return parser, parser.parse_args()


def validate_provision_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    """Validate provision only arguments"""
    missing = [
        flag
        for flag, val in [
            ("--image", args.image),
            ("--network", args.network),
            ("--secgroup", args.secgroup),
            ("--controller-flavour", args.controller_flavour),
            ("--nodes-flavour", args.nodes_flavour),
            ("--cluster-ip-range", args.cluster_ip_range),
            ("--mariadb-pass", args.mariadb_pass),
            ("--ansible-key", args.ansible_key),
        ]
        if not val
    ]
    if missing:
        parser.error(
            f"The following arguments are required for provisioning: {', '.join(missing)}"
        )


def cluster_node_names(args: argparse.Namespace) -> list[str]:
    """Return node names as list."""
    return [args.controller_name] + [
        f"{args.nodes_prefix}-{i}" for i in range(1, args.nodes_count + 1)
    ]


def provision_node(name: str, flavour: str, args: argparse.Namespace) -> dict:
    """Create an OpenStack VM and return name, IP, and ID."""
    ostack = OStack()
    params = {
        "openstack_image": args.image,
        "openstack_network": args.network,
        "openstack_security_groups": args.secgroup,
        "openstack_flavor": flavour,
    }

    try:
        logger.info("Creating VM: '%s' (flavour: %s)...", name, flavour)
        vm = ostack.create(name, params)
        if not vm:
            raise RuntimeError(f"Failed to create VM for: '{name}'")

        vm = ostack.wait_for_active(vm)
        if not vm:
            raise RuntimeError(f"VM '{name}' failed to reach ACTIVE state")

        ip = ostack.get_server_ip(vm, args.network)
        if not ip:
            raise RuntimeError(f"Failed to get IP for VM: '{name}'")

        logger.info("VM '%s' is ACTIVE at %s", name, ip)
        return {"name": name, "ip": ip, "id": vm.id}
    finally:
        ostack.disconnect()


def provision_cluster(args: argparse.Namespace) -> None:
    """Create all VMs in parallel and run Ansible."""
    names = cluster_node_names(args)
    flavours = [args.controller_flavour] + [args.nodes_flavour] * args.nodes_count

    logger.info("Provisioning %d nodes in parallel...", len(names))
    try:
        with ThreadPoolExecutor(max_workers=len(names)) as executor:
            results = list(
                executor.map(
                    lambda name, flavour: provision_node(name, flavour, args),
                    names,
                    flavours,
                )
            )
    except Exception as exc:
        logger.error("Provisioning failed: %s", exc)
        sys.exit(1)

    controller, *workers = results
    run_ansible(controller, workers, args)


def write_inventory(
    controller: dict, workers: list[dict], args: argparse.Namespace
) -> str:
    """Write Ansible JSON inventory file and return its path."""
    inventory = {
        "all": {
            "vars": {
                "slurm_cluster_name": args.cluster_name,
                "slurm_controller_hostname": controller["name"],
                "slurm_controller_ip": controller["ip"],
                "slurm_worker_nodes": [
                    {"hostname": w["name"], "ip": w["ip"]} for w in workers
                ],
            },
            "children": {
                "slurm_controller": {
                    "hosts": {
                        controller["ip"]: {
                            "slurm_mariadb_pass": args.mariadb_pass,
                            "cluster_ip_range": args.cluster_ip_range,
                        }
                    }
                },
                "slurm_worker": {"hosts": {w["ip"]: {} for w in workers}},
            },
        }
    }

    path = f"inventory_{args.cluster_name}.json"
    with open(path, "w") as f:
        json.dump(inventory, f, indent=2)

    logger.info("Inventory written to %s", path)
    return path


def generate_key(path: str, size: int) -> None:
    """Generate a key file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "wb") as f:
        f.write(secrets.token_bytes(size))
    # Set perms to 400 locally, this will be set on nodes by ansible
    os.chmod(path, 0o400)
    logger.info("Key generated at %s", path)


def run_ansible(
    controller: dict, workers: list[dict], args: argparse.Namespace
) -> None:
    """Write the inventory and run the Ansible deployment playbook."""
    if not os.path.exists(PLAYBOOK):
        logger.error("Playbook not found: %s", os.path.abspath(PLAYBOOK))
        sys.exit(1)

    generate_key("roles/slurm/common/files/munge.key", 1024)
    generate_key("roles/slurm/controller/files/jwt_hs256.key", 32)

    inv_path = write_inventory(controller, workers, args)

    cmd = [
        "ansible-playbook",
        "-i",
        inv_path,
        "--private-key",
        args.ansible_key,
        PLAYBOOK,
    ]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd)

    if result.returncode != 0:
        logger.error("Ansible failed, exit code: %d", result.returncode)
        sys.exit(result.returncode)

    logger.info("Deployment complete!")


def destroy_cluster(args: argparse.Namespace) -> None:
    """Delete all cluster nodes."""
    ostack = OStack()
    targets = cluster_node_names(args)

    logger.info("Deleting nodes: %s", ", ".join(targets))
    try:
        for name in targets:
            ostack.delete(name)
    finally:
        ostack.disconnect()

    logger.info("Cluster destroyed successfully.")


if __name__ == "__main__":
    main()
