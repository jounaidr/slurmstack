"""
Helper functions for interacting with OpenStack
"""

import logging
import socket
import subprocess
from ipaddress import IPv4Network
from typing import Dict

from config import PoolManagerConfig
from openstack import connection
from openstack.exceptions import ResourceNotFound

logger = logging.getLogger(__name__)


class OStack:
    """
    Helper functions for interacting with OpenStack
    """

    def __init__(self, cloud_details: list, config: PoolManagerConfig):
        self.cloud_connections = self._set_cloud_connections(cloud_details)
        self.spec_cloud_details: Dict = {}
        self.conn = None
        self.config = config

    def _set_cloud_connections(self, cloud_details: list) -> dict:
        """Initialise all the cloud connections"""
        connections = {}
        for cloud in cloud_details:
            connections[cloud["_id"]] = cloud
        return connections

    def connect(self, cloud_id: str):
        """Authenticate with OpenStack and open a connection"""
        self.spec_cloud_details = self.cloud_connections[cloud_id]
        region_name = self.spec_cloud_details.get("region_name", None)

        self.conn = connection.Connection(
            region_name=region_name,
            auth={
                "auth_url": self.spec_cloud_details["url"],
                "username": self.spec_cloud_details["username"],
                "password": self.spec_cloud_details["password"],
                "project_name": self.spec_cloud_details["parameters"]["project_name"],
                "project_domain_name": self.spec_cloud_details["parameters"][
                    "project_domain_name"
                ],
                "user_domain_name": self.spec_cloud_details["parameters"][
                    "user_domain_name"
                ],
            },
        )

    def disconnect(self):
        """Close connection with OpenStack"""
        self.conn.close()

    def create(self, name, parameters):
        """
        Ask OpenStack to create a Virtual Machine with supplied parameters
        parameters must contain:
        openstack_image
        openstack_flavor
        openstack_network
        openstack_security_groups

        Returns None on failure
        Returns OpenStack Server object on success
        """
        virtual_machine = None
        try:
            image = self.conn.compute.find_image(parameters["openstack_image"])
            flavor = self.conn.compute.find_flavor(parameters["openstack_flavor"])
            network = self.conn.network.find_network(parameters["openstack_network"])

            security_groups = [
                {"name": security_group}
                for security_group in parameters["openstack_security_groups"]
            ]
            virtual_machine = self.conn.compute.create_server(
                name=name,
                image_id=image.id,
                flavor_id=flavor.id,
                networks=[{"uuid": network.id}],
                security_groups=security_groups,
            )
        except Exception:  # pylint: disable=broad-except
            logger.exception("Error trying to create VM: %s %s", name, parameters)
        return virtual_machine

    def shutdown(self, vmid):
        """Ask OpenStack to shutdown a Virtual Machine"""
        try:
            self.conn.compute.stop_server(vmid)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Error trying to shutdown VM: %s", vmid)

    def delete(self, vmid):
        """Ask OpenStack to delete a Virtual Machine"""
        try:
            self.conn.compute.delete_server(vmid)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Error trying to delete VM: %s", vmid)

    def get_status(self, vmid: str) -> str | None:
        """Get Virtual Machine status from OpenStack"""
        # https://docs.openstack.org/api-guide/compute/server_concepts.html
        status = None
        try:
            status = self.conn.compute.get_server(vmid).status  # type: ignore
        except ResourceNotFound:
            status = "DELETED"
        except Exception:  # pylint: disable=broad-except
            logger.exception("Error when checking status of vm with ID: %s", vmid)
        return status

    def get_hostname(self, vmid: str, parameters: dict) -> None | str:
        """Get Virtual Machine hostname"""
        hostname = None
        try:
            virtual_machine = self.conn.compute.get_server(vmid)  # type: ignore
            ip_address = virtual_machine.addresses[parameters["openstack_network"]][0][
                "addr"
            ]
            hostname = socket.gethostbyaddr(ip_address)[0]
        except Exception:  # pylint: disable=broad-except
            logger.exception("Error obtaining hostname of VM: %s", vmid)
        return hostname

    def add_to_dns(self, vmid: str, network_name: str):
        """
        This is only to be used when the pool manager is deployed on an external cloud
        """
        logger.info("Adding DNS record for VM: %s", vmid)
        ip_address, hostname, reverse_dns_zone = self._get_details_for_dns_record(
            vmid, network_name
        )

        cmd = [
            "sh",
            "./modify-dns-records.sh",
            "add",
            ip_address,
            hostname,
            self.config.dns_config.dns_server_ip,
            self.config.dns_config.domain,
            f"{reverse_dns_zone}.in-addr.arpa",
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            logger.exception("Error adding VM %s DNS record", vmid)

    def remove_from_dns(self, vmid: str, network_name: str):
        """
        This is only to be used when the pool manager is deployed on an external cloud
        """
        logger.info("Removing DNS record for VM: %s", vmid)
        ip_address, hostname, reverse_dns_zone = self._get_details_for_dns_record(
            vmid, network_name
        )

        cmd = [
            "sh",
            "./modify-dns-records.sh",
            "remove",
            ip_address,
            hostname,
            self.config.dns_config.dns_server_ip,
            self.config.dns_config.domain,
            f"{reverse_dns_zone}.in-addr.arpa",
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            logger.exception("Error removing VM %s DNS record", vmid)

    def _get_details_for_dns_record(self, vmid: str, network_name: str):
        try:
            virtual_machine = self.conn.compute.get_server(vmid)  # type: ignore
            ip_address = virtual_machine.addresses[network_name][0]["addr"]

            network = self.conn.network.find_network(network_name)  # type: ignore
            subnet = self.conn.get_subnet(network.subnet_ids[0])  # type: ignore
            network_address = IPv4Network(subnet.cidr).network_address
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Error obtaining VM: %s or network: %s information", vmid, network_name
            )
            raise exc

        vm_ip_parts = ip_address.split(".")
        hostname = (
            f"host-{vm_ip_parts[0]}-{vm_ip_parts[1]}-{vm_ip_parts[2]}-{vm_ip_parts[3]}"
        )

        network_address_parts = list(
            filter(lambda ip_part: ip_part != "0", str(network_address).split("."))
        )
        reverse_dns_zone = ".".join(network_address_parts[::-1])

        return ip_address, hostname, reverse_dns_zone