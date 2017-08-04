import libzfs
import subprocess

import iocage.lib.JailConfig
import iocage.lib.Network
import iocage.lib.Storage
import iocage.lib.helpers

class Jail:

  def __init__(self, data = {}, zfs=None, host=None):

    iocage.lib.helpers.init_zfs(self, zfs)
    iocage.lib.helpers.init_host(self, host)

    self.config = iocage.lib.JailConfig.JailConfig(data=data)
    self.networks = []
    self.storage = iocage.lib.Storage.Storage(jail=self, auto_create=True, safe_mode=False)

    try:
      self.config.dataset = self.dataset
      self.config.read()
    except:
      pass

  @property
  def zfs_pool_name(self):
    return self.host.datasets.root_dataset.name.split("/", maxsplit=1)[0]

  def start(self):
    self.require_jail_existing()
    self.require_jail_stopped()
    self.storage.umount_nullfs()
    self.launch_jail()
    if self.config.vnet:
      self.start_network()
      self.set_routes()
    self.set_nameserver()
    self.storage.apply()

  def stop(self):
    self.require_jail_existing()
    self.require_jail_running()
    self.destroy_jail()

  def exec(self, command):
    command = [
      "/usr/sbin/jexec",
      self.identifier
    ] + command
    return iocage.lib.helpers.exec(command)

  def destroy_jail(self):

    command = [ "jail", "-r" ]
    command.append(self.identifier)

    subprocess.check_output(command, shell=False, stderr=subprocess.DEVNULL)

  def launch_jail(self):

    command = [ "jail", "-c" ]

    if self.config.vnet:
      command.append('vnet')
    else:
      command += [
        f"ip4.addr={self.config.ip4_addr}",
        f"ip4.saddrsel={self.config.ip4_saddrsel}",
        f"ip4={self.config.ip4}",
        f"ip6.addr={self.config.ip6_addr}",
        f"ip6.saddrsel={self.config.ip6_saddrsel}",
        f"ip6={self.config.ip6}"
      ]

    command += [
      f"name={self.identifier}",
      f"host.hostname={self.config.host_hostname}",
      f"host.domainname={self.config.host_domainname}",
      f"path={self.path}/root",
      #f"securelevel={securelevel}",
      f"host.hostuuid={self.uuid}",
      f"devfs_ruleset={self.config.devfs_ruleset}",
      f"enforce_statfs={self.config.enforce_statfs}",
      f"children.max={self.config.children_max}",
      f"allow.set_hostname={self.config.allow_set_hostname}",
      f"allow.sysvipc={self.config.allow_sysvipc}"
    ]

    if self.host.userland_version > 10.3:
      command += [
        f"sysvmsg={self.config.sysvmsg}",
        f"sysvsem={self.config.sysvsem}",
        f"sysvshm={self.config.sysvshm}"
      ]

    command += [
      f"allow.raw_sockets={self.config.allow_raw_sockets}",
      f"allow.chflags={self.config.allow_chflags}",
      f"allow.mount={self.config.allow_mount}",
      f"allow.mount.devfs={self.config.allow_mount_devfs}",
      f"allow.mount.nullfs={self.config.allow_mount_nullfs}",
      f"allow.mount.procfs={self.config.allow_mount_procfs}",
      f"allow.mount.zfs={self.config.allow_mount_zfs}",
      f"allow.quotas={self.config.allow_quotas}",
      f"allow.socket_af={self.config.allow_socket_af}",
      f"exec.prestart={self.config.exec_prestart}",
      f"exec.poststart={self.config.exec_poststart}",
      f"exec.prestop={self.config.exec_prestop}",
      f"exec.stop={self.config.exec_stop}",
      f"exec.clean={self.config.exec_clean}",
      f"exec.timeout={self.config.exec_timeout}",
      f"stop.timeout={self.config.stop_timeout}",
      f"mount.fstab={self.path}/fstab",
      f"mount.devfs={self.config.mount_devfs}"
    ]

    if self.host.userland_version > 9.3:
      command += [
        f"mount.fdescfs={self.config.mount_fdescfs}",
        f"allow.mount.tmpfs={self.config.allow_mount_tmpfs}"
      ]

    command += [
      "allow.dying",
      f"exec.consolelog={self.logfile_path}",
      "persist"
    ]

    try:
      output = subprocess.check_output(command, shell=False, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
      print("Failed", exc.returncode, exc.output)
      raise

  def start_network(self):

    if not self.config.vnet:
      # Not necessary without VNET
      return

    nics = self.config.interfaces
    for nic in nics:

      bridges = list(self.config.interfaces[nic])

      try:
        ipv4_addresses = self.config.ip4_addr[nic]
      except:
        ipv4_addresses = []

      try:
        ipv6_addresses = self.config.ip6_addr[nic]
      except:
        ipv6_addresses = []

      net = iocage.lib.Network.Network(jail=self, nic=nic, ipv4_addresses=ipv4_addresses, ipv6_addresses=ipv6_addresses, bridges=bridges)
      net.setup()
      self.networks.append(net)

  def set_nameserver(self):
    self.config.resolver.apply(self)

  def set_routes(self):

    if self.config.defaultrouter:
      self._set_route(self.config.defaultrouter)

    if self.config.defaultrouter6:
      self._set_route(self.config.defaultrouter6, ipv6=True)

  def _set_route(self, gateway, ipv6=False):

    command = [
      "/sbin/route",
      "add"
    ] + (["-6"] if ipv6 else []) + [
      "default",
      gateway
    ]

    self.exec(command)

  def require_jail_existing(self):
    if not self.exists:
      raise Exception(f"Jail {self.humanreadable_name} does not exist")

  def require_jail_stopped(self):
    if self.running:
      raise Exception(f"Jail {self.humanreadable_name} is already running")

  def require_jail_running(self):
    if not self.running:
      raise Exception(f"Jail {self.humanreadable_name} is not running")

  def _get_humanreadable_name(self):

    try:
      return self.config.name
    except:
      pass

    try:
      return self.config.uuid
    except:
      pass

    raise "This Jail does not have any identifier yet"

  def _get_stopped(self):
    return self.running != True;

  def _get_running(self):
    return self._get_jid() != None

  def _get_jid(self):
    try:
      stdout = subprocess.check_output([
        "/usr/sbin/jls",
        "-j",
        self.identifier,
        "-v",
        "jid"
      ], shell=False, stderr=subprocess.DEVNULL)
      jid = stdout.decode("utf-8").strip()
    except:
      jid = None

    return jid

  def _get_identifier(self):
    return f"ioc-{self.uuid}"

  def _get_exists(self):
    try:
      self.dataset
      return True
    except:
      return False

  def _get_uuid(self):
    return self.config.uuid

  def _get_dataset_name(self):
    return f"{self.host.datasets.root_dataset.name}/jails/{self.config.uuid}"

  def _get_dataset(self):
    return self.zfs.get_dataset(self._get_dataset_name())

  def _get_path(self):
    return self.dataset.mountpoint

  def _get_logfile_path(self):
    return f"{self.host.datasets.root_dataset.mountpoint}/log/{self.identifier}-console.log"

  def __getattr__(self, key):
    try:
      method = self.__getattribute__(f"_get_{key}")
      return method()
    except:
      raise Exception(f"Jail property {key} not found")
