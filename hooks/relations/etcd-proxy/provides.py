#!/usr/bin/python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from charms.reactive import RelationBase
from charms.reactive import hook
from charms.reactive import scopes


class EtcdProvider(RelationBase):
    scope = scopes.GLOBAL

    @hook('{provides:etcd-proxy}-relation-{joined,changed}')
    def joined_or_changed(self):
        ''' Set state so the unit can identify it is connecting '''
        self.set_state('{relation_name}.connected')

    @hook('{provides:etcd-proxy}-relation-{broken,departed}')
    def broken_or_departed(self):
        ''' Set state so the unit can identify it is departing '''
        self.remove_state('{relation_name}.connected')

    def set_client_credentials(self, key, cert, ca):
        ''' Set the client credentials on the global conversation for this
        relation. '''
        self.set_remote('client_key', key)
        self.set_remote('client_ca', ca)
        self.set_remote('client_cert', cert)

    def set_cluster_string(self, cluster_string):
        ''' Set the cluster string on the convsersation '''
        self.set_remote('cluster', cluster_string)

    # Kept for backwords compatibility
    def provide_cluster_string(self, cluster_string):
        '''
        @params cluster_string - fully formed etcd cluster string.
        This is akin to the --initial-cluster-string setting to the
        etcd-daemon. Proxy's will need to know each declared member of
        the cluster to effectively proxy.
        '''
        self.set_remote('cluster', cluster_string)
