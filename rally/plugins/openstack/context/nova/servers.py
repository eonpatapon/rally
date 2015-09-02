# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from rally.common.i18n import _
from rally.common import log as logging
from rally.common import utils as rutils
from rally import consts
from rally import osclients
from rally.plugins.openstack.context.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.task import context
from rally.task import types


LOG = logging.getLogger(__name__)


@context.configure(name="servers", order=430)
class ServerGenerator(context.Context):
    """Context class for adding temporary servers for benchmarks.

        Servers are added for each tenant.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "image": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    }
                }
            },
            "flavor": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    }
                }
            },
            "servers_per_tenant": {
                "type": "integer",
                "minimum": 1
            },
        },
        "required": ["image", "flavor"],
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "servers_per_tenant": 5
    }

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `Servers`"))
    def setup(self):
        image = self.config["image"]
        flavor = self.config["flavor"]
        servers_per_tenant = self.config["servers_per_tenant"]

        clients = osclients.Clients(self.context["users"][0]["endpoint"])
        image_id = types.ImageResourceType.transform(clients=clients,
                                                     resource_config=image)
        flavor_id = types.FlavorResourceType.transform(clients=clients,
                                                       resource_config=flavor)

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            LOG.debug("Booting servers for user tenant %s "
                      % (user["tenant_id"]))
            nova_scenario = nova_utils.NovaScenario({"user": user})

            LOG.debug("Calling _boot_servers with image_id=%(image_id)s "
                      "flavor_id=%(flavor_id)s "
                      "servers_per_tenant=%(servers_per_tenant)s"
                      % {"image_id": image_id,
                         "flavor_id": flavor_id,
                         "servers_per_tenant": servers_per_tenant})

            servers = nova_scenario._boot_servers(image_id, flavor_id,
                                                  servers_per_tenant)

            current_servers = [server.id for server in servers]

            LOG.debug("Adding booted servers %s to context"
                      % current_servers)

            self.context["tenants"][tenant_id][
                "servers"] = current_servers

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `Servers`"))
    def cleanup(self):
        resource_manager.cleanup(names=["nova.servers"],
                                 users=self.context.get("users", []))


@context.configure(name="network_servers", order=431)
class NetworkServerGenerator(context.Context):
    """Context class for adding temporary servers for benchmarks.

        Servers are added for each network.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "image": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    }
                }
            },
            "flavor": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    }
                }
            },
            "servers_per_network": {
                "type": "integer",
                "minimum": 1
            },
        },
        "required": ["image", "flavor"],
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "servers_per_network": 2,
    }

    @rutils.log_task_wrapper(LOG.info, _("Enter context: `NetworkServers`"))
    def setup(self):
        image = self.config["image"]
        flavor = self.config["flavor"]
        servers_per_network = self.config["servers_per_network"]

        clients = osclients.Clients(self.context["users"][0]["endpoint"])
        image_id = types.ImageResourceType.transform(clients=clients,
                                                     resource_config=image)
        flavor_id = types.FlavorResourceType.transform(clients=clients,
                                                       resource_config=flavor)

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            for index, network in enumerate(self.context["tenants"][tenant_id]["networks"]):
                LOG.debug("Booting servers for user tenant %s in network %s"
                          % (user["tenant_id"], network["id"]))
                nova_scenario = nova_utils.NovaScenario({"user": user})

                LOG.info("Calling _boot_servers with image_id=%(image_id)s "
                         "flavor_id=%(flavor_id)s "
                         "servers_per_network=%(servers_per_network)s "
                         "net-id=%(net-id)s"
                         % {"image_id": image_id,
                            "flavor_id": flavor_id,
                            "servers_per_network": servers_per_network,
                            "net-id": network["id"]})

                servers = nova_scenario._boot_servers(image_id, flavor_id,
                                                      servers_per_network,
                                                      nics=[{"net-id": network["id"]}])
                current_servers = [server.id for server in servers]

                LOG.info("Adding booted servers %s to context" % current_servers)

                self.context["tenants"][tenant_id]["networks"][index]["servers"] = current_servers

    @rutils.log_task_wrapper(LOG.info, _("Exit context: `NetworkServers`"))
    def cleanup(self):
        resource_manager.cleanup(names=["nova.servers"],
                                 users=self.context.get("users", []))
