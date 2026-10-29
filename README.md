# SlurmStack

*SlurmStack* is a lightweight, automated tool for provisioning a SLURM cluster on **OpenStack**. Built with **Ansible** for **Rocky Linux 9**, this project focuses on providing a minimal, uncomplicated configuration that is easy to modify and run manually. Because it includes a native deployment of `slurmrestd`, *SlurmStack* is ideal for setting up a preproduction environment to test or develop services based on the SLURM REST API.
> [!NOTE]  
> This project is designed for testing and development. Whilst it can be modified for production use, it should not be considered production-ready out of the box.
>
> Consider using [Slinky](https://github.com/SlinkyProject) for a more complete production ready solution.

---

### Installation

<ins>Requirements:</ins>

- Python 3.11+
- pip

Clone the repository and install the **Python/Ansible** dependencies:

```bash
git clone <repo-url>
cd slurmstack
pip install -e .
ansible-galaxy collection install -r requirements.yml
```

---

### Prerequisites

The following must be in place within your **OpenStack** project before running _SlurmStack_.

<ins>OpenStack credentials:</ins>

The **OpenStack** credentials can be set using a `clouds.yaml` file, or via the respective environment variables within `.env`.

To obtain a `clouds.yaml` file from your **OpenStack** Horizon dashboard, do the following:

1. Log into Horizon
2. On the left bar, click Identity.
3. Under Identity, click "Application Credentials".
4. Click the "+ Create Application Credentials" button in the top bar.
5. You must provide at least a name.
6. Click "Create Application Credential" at the bottom of the page.
7. Click Download clouds.yaml.

You can also create a `clouds.yaml` file manually using the provided example:

```bash
cp clouds.yaml.example clouds.yaml
```

<ins>Rocky Linux 9 image:</ins>

A **Rocky Linux 9** image must be available in your **OpenStack** project. The image name is set via `SS_IMAGE`. Base images can be found on the [Rocky Linux download webpage](https://rockylinux.org/download).

<ins>Network:</ins>

A network must exist for the **OpenStack** project, which must be accessible to the VMs. The network name can be set via `SS_NETWORK`.

<ins>Security groups:</ins>

One or more security groups must be pre-created in **OpenStack** and assigned to the VMs via `SS_SECGROUP`. At a minimum, the groups should allow:

- SSH (port 22) from your control machine
- All internal traffic between cluster nodes

<ins>SSH key pair:</ins>

An SSH key pair must be registered in **OpenStack**, and the corresponding private key must be accessible on the machine running _SlurmStack_. Set the path via SS_ANSIBLE_KEY. Ansible uses this key to connect to the provisioned VMs.

---

### Run

_SlurmStack_ has two configuration methods available, using an `.env` file or using the CLI options. Either copy the example environment file and fill in your values as follows:

```bash
cp .env.example .env
```

Or supply the required CLI arguments when running _SlurmStack_. Note that the CLI arguments take precedence over the `.env` file. You can supply `--help` for the full argument reference:

```
usage: slurmstack.py [-h] [--destroy] [-clu CLUSTER_NAME] [-con CONTROLLER_NAME]
                     [-np NODES_PREFIX] [-nc NODES_COUNT] [-i IMAGE] [-net NETWORK]
                     [-s SECGROUP [SECGROUP ...]] [-cf CONTROLLER_FLAVOUR]
                     [-nf NODES_FLAVOUR] [-cr CLUSTER_IP_RANGE] [-mp MARIADB_PASS]
                     [-k ANSIBLE_KEY]

Provision a Slurm cluster on OpenStack and deploy it with Ansible.

options:
  --destroy                   Tear down all cluster VMs
  -clu, --cluster-name        Name of the Slurm cluster
  -con, --controller-name     Name of the controller VM
  -np,  --nodes-prefix        Prefix for worker node names (e.g. slurm-worker → slurm-worker-1)
  -nc,  --nodes-count         Number of worker nodes
  -i,   --image               OpenStack image name
  -net, --network             OpenStack network name
  -s,   --secgroup            Security group names, comma-separated
  -cf,  --controller-flavour  Flavour for the controller VM
  -nf,  --nodes-flavour       Flavour for worker VMs
  -cr,  --cluster-ip-range    IP range for NFS exports (e.g. 10.0.0.0/24)
  -mp,  --mariadb-pass        MariaDB password for Slurm accounting
  -k,   --ansible-key         Path to SSH private key for Ansible
```

If the Ansible run fails, you can manually restart the playbook via: `ansible-playbook -i inventory_<cluster-name>.json --private-key /path/to/key playbooks/deploy_nodes.yml`
