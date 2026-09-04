"""
Helper functions for interacting with OpenStack
"""

import logging
import socket
import openstack

logger = logging.getLogger(__name__)


class OStack:
    """
    Helper functions for interacting with OpenStack
    """
    
    def __init__(self):
        """Initialize OpenStack connection."""
        self.conn = openstack.connect()

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
