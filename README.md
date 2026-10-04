# SlurmStack

*SlurmStack* is a lightweight, automated tool for provisioning a SLURM cluster on **OpenStack**. Built with **Ansible** for **Rocky Linux 9**, this project focuses on providing a minimal, uncomplicated configuration that is easy to modify and run manually. Because it includes a native deployment of `slurmrestd`, *SlurmStack* is ideal for setting up a preproduction environment to test or develop services based on the SLURM REST API.
> [!NOTE]  
> This project is designed for testing and development. Whilst it can be modified for production use, it should not be considered production-ready out of the box.
>
> Consider using [Slinky](https://github.com/SlinkyProject) for a more complete production ready solution.

---

### Installation

<ins>Requirements</ins>

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

The following must be in place in your **OpenStack** project before running _SlurmStack_.

<ins>OpenStack credentials</ins>

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

<ins>Rocky Linux 9 image</ins>

A **Rocky Linux 9** image must be available in your **OpenStack** project. The image name is set via `SS_IMAGE`. Base images can be found on the [Rocky Linux download webpage](https://rockylinux.org/download).

<ins>Network</ins>

A network must exist for the **OpenStack** project, which must be accessible to the VMs. The network name can be set via `SS_NETWORK`.

---

### Run

if ansible fails run: `ansible-playbook -i inventory_<cluster-name>.json --private-key /path/to/key playbooks/deploy_nodes.yml`
