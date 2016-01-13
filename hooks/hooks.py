#!/usr/bin/env python
from charmhelpers.core import hookenv
from charmhelpers.core import unitdata
from charmhelpers.core import templating
from charmhelpers.core import host
from charmhelpers import fetch
from os import environ
from path import path
import string
import random
import shlex
from subprocess import check_call
import sys

hooks = hookenv.Hooks()
hook_data = unitdata.HookData()
db = unitdata.kv()

status_set = hookenv.status_set
private_address = hookenv.unit_get('private-address')
public_address = hookenv.unit_get('private-address')
unit_name = environ['JUJU_UNIT_NAME'].replace('/', '')

try:
    leader_status = hookenv.is_leader()
except NotImplementedError:
    hookenv.log('This charm requires Leader Election. Juju >= 1.23.2.'
                ' Leader election binary not found, Panic and exit!',
                'CRITICAL')
    status_set('blocked', 'Requires Leader Election - juju >= 1.23.2')
    sys.exit(1)


@hooks.hook('config-changed')
def config_changed():
    if not db.get('installed') or hookenv.config().changed('source-sum'):
        status_set("maintenance", "Installing etcd.")
        install_etcd()
    if leader_status:
        status_set('maintenance', "I am the leader, configuring single node")
        cluster_data = {'token': cluster_token()}
        cluster_data['cluster_state'] = 'new'
        cluster_data['cluster'] = cluster_string()
        main(cluster_data)


@hooks.hook('cluster-relation-changed')
def cluster_relation_changed():
    cluster_data = {}
    # Useful when doing runtime based configuration. (units added after cluster
    # bootstrap) see docs:
    # https://github.com/coreos/etcd/blob/master/Documentation/runtime-configuration.md
    if leader_status:
        token = cluster_token()
        print 'Initializing cluster with {}'.format(token)
        hookenv.relation_set(hookenv.relation_id(),
                             {'leader-address': private_address,
                              'cluster-state': 'existing',
                              'cluster-token': token,
                              'cluster': cluster_string()})
        cluster_data['cluster'] = cluster_string()

    if not leader_status:
        # A token is only generated once on a cluster.
        token = hookenv.relation_get('cluster-token')
        cluster_data['cluster'] = hookenv.relation_get('cluster')

    if not token:
        status_set("blocked", "No token available on relationship - exiting")
        return
    cluster_data['token'] = token
    main(cluster_data)


@hooks.hook('proxy-relation-changed')
def proxy_relation_changed():
    hookenv.relation_set(hookenv.relation_id(),
                         {'cluster': cluster_string()})


def main(cluster_data={}):

    # Grab the boilerplate config entries
    cluster_data['unit_name'] = environ['JUJU_UNIT_NAME'].replace('/', '')
    cluster_data['private_address'] = private_address
    cluster_data['public_address'] = public_address
    cluster_data['cluster_state'] = 'new'

    if not leader_status:
        cluster_data['cluster_state'] = hookenv.relation_get('cluster-state')
        leader_address = hookenv.relation_get('leader-address')

        # do self registration
        if not db.get('registered'):
            cmd = "/opt/etcd/etcdctl -C http://{}:4001 member add {}" \
                  " http://{}:7001".format(leader_address,
                                           cluster_data['unit_name'],
                                           private_address)
            print(cmd)
            check_call(shlex.split(cmd))
            db.set('registered', True)

    # introspect the cluster, and form the cluster string.
    # https://github.com/coreos/etcd/blob/master/Documentation/configuration.md#-initial-cluster

    templating.render('etcd.conf.jinja2', '/etc/init/etcd.conf',
                      cluster_data, owner='root', group='root')

    host.service('restart', 'etcd')
    if leader_status:
        status_set('active', 'Etcd leader running')
    else:
        status_set('active', 'Etcd follower running')


def cluster_string():
    cluster = ""
    cluster_rels = hook_data.rels['cluster'][1].keys()
    # introspect the cluster, and form the cluster string.
    # https://github.com/coreos/etcd/blob/master/Documentation/configuration.md#-initial-cluster
    if hook_data.rels['cluster'][1]:
        reldata = hook_data.rels['cluster'][1][cluster_rels[0]]
        for unit in reldata:
            private = reldata[unit]['private-address']
            cluster = '{}{}=http://{}:7001,'.format(cluster,
                                                    unit.replace('/', ''),
                                                    private)
    else:
        cluster = "{}=http://{}:7001".format(unit_name, private_address)

    return cluster.rstrip(',')


def cluster_token():
    if not db.get('cluster-token'):
        token = id_generator()
        db.set('cluster-token', token)
        return token
    return db.get('cluster-token')


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def install_etcd():
    source = hookenv.config('bin-source')
    sha = hookenv.config('source-sum')

    unpack = fetch.install_remote(source, 'fetched', sha)

    # Copy the payload into place on the system
    etcd_dir = path('/opt/etcd')
    unpack_dir = path(unpack)
    for d in unpack_dir.dirs():
        d = path(d)
        for f in d.files():
            f.copy(etcd_dir)

    for executable in "etcd", "etcdctl":
        origin = etcd_dir / executable
        target = path('/usr/local/bin/%s' % executable)
        target.exists() and target.remove()
        origin.symlink(target)

    hookenv.open_port(4001)
    db.set('installed', True)

if __name__ == '__main__':
    with hook_data():
        hooks.execute(sys.argv)
