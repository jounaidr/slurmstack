"""
Helper functions for interacting with OpenStack
"""

import logging
import openstack

logger = logging.getLogger(__name__)


class OStack:
    """
    Helper functions for interacting with OpenStack
    """

    def __init__(self) -> None:
        """Initialize OpenStack connection."""
        self.conn = None
        self.conn = openstack.connect()

    def __init__(self) -> None:
        """Close connection with OpenStack"""
        if self.conn:
            self.conn.close()

    def create(self, name: str, parameters: dict) -> object | None:
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

    def wait_for_active(self, server, wait: int = 300) -> object | None:
        """Wait until the OpenStack server reaches ACTIVE status."""
        try:
            return self.conn.compute.wait_for_server(server, wait=wait)
        except Exception:
            logger.exception("Timeout or error waiting for server %s", getattr(server, 'name', 'unknown'))
            return None

    def get_server_ip(self, server, network_name: str) -> str | None:
        """Extract the IPv4 address from an OpenStack server object."""
        try:
            addresses = server.addresses.get(network_name, [])
            for addr in addresses:
                if addr.get("version") == 4 or ":" not in addr.get("addr", ""):
                    return addr["addr"]
        except Exception:
            logger.exception("Failed to extract IP for server %s", getattr(server, 'name', 'unknown'))
        return None

    def delete(self, vmid: str) -> None:
        """Ask OpenStack to delete a Virtual Machine"""
        try:
            server = self.conn.compute.find_server(vmid)
            if not server:
                logger.debug("VM '%s' not found — skipping deletion", vmid)
                return
            self.conn.compute.delete_server(server.id)
            logger.info("Deleted OpenStack VM: %s", vmid)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Error trying to delete VM: %s", vmid)
