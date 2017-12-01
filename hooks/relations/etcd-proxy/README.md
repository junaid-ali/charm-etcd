# Overview

This interface layer handles the communication with Etcd via the `etcd-proxy` interface.

# Usage

## Requires

This interface layer will set the following states, as appropriate:

  * `{relation_name}.connected` The relation is established, but Etcd may not
  yet have provided any connection or service information.

  * `{relation_name}.available` Etcd has provided its cluster string
    information, and is ready to handle incoming connections.
    The provided information can be accessed via the following methods:
      * `cluster_string()`

  * `{relation_name}.tls.available` Etcd has provided client
  connection credentials for TLS communication.
      * `client_ca` - CA certificate
      * `client_cert` - Client Cert
      * `client_key` - Client Key


For example, a common application for this is configuring an
applications backend kv storage, like Docker.

```python
@when('proxy.available')
def prepare_etcd_proxy(proxy):
    con_string = proxy.cluster_string()
    # Save certificates to disk
    proxy.save_client_credentials('/etc/ssl/etcd')
    opts = {}
    opts['cluster_string'] = con_string
    opts['client_ca'] = '/etc/ssl/etcd/client-ca.pem'
    opts['client_cert'] = '/etc/ssl/etcd/client-cert.pem'
    opts['client_key'] = '/etc/ssl/etcd/client-key.pem'
    render('proxy_systemd_template', '/etc/systemd/system/etcd-proxy.service', opts)

```


## Provides

A charm providing this interface is providing the Etcd cluster management
connection string. This is similar to what ETCD requires when peering, declared as:

```shell
etcd0=https://192.168.1.2:2380,etcd1=https://192.168.2.22:2380
```

This interface layer will set the following states, as appropriate:

  * `{relation_name}.connected` One or more clients of any type
  have been related.  The charm should call the following
  methods to provide the appropriate information to the clients:

    * `{relation_name}.provide_cluster_string()`

  * Additionally to secure the Etcd network connections, All of
  the client certificate keys must be set, which is conveniently
  enabled as a method on the interface:


#### Example:

```python
@when('proxy.connected')
def send_cluster_details(proxy):
    bag = EtcdDatabag()
    # Read the client credentials
    ca = read_file_contents('/etc/ssl/etcd/ca.pem')
    cert = read_file_contents('/etc/ssl/etcd/client-cert.pem')
    key = read_file_contents('/etc/ssl/etcd/client-key.pem')
    # Set the cluster string for bootstrap
    proxy.set_cluster_string(bag.cluster_string())
    # Set the client credentials
    proxy.set_client_credentials(key, cert, ca)

def read_file_contents(filepath):
    with open(filepath, 'r') as fp:
        return fp.read(filepath)
```


# Contact Information

### Maintainer
- Charles Butler &lt;[charles.butler@canonical.com](mailto:charles.butler@canonical.com)&gt;

### Contributors
- Mathew Bruzek  &lt;[mathew.bruzek@canonical.com](mailto:mathew.bruzek@canonical.com)&gt;

# Etcd

- [Etcd](https://coreos.com/etcd/) home page
- [Etcd bug trackers](https://github.com/coreos/etcd/issues)
- [Etcd Juju Charm](http://github.com/juju-solutions/layer-etcd)
