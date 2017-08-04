import iocage.lib.JailConfigJSON
import iocage.lib.JailConfigInterfaces
import iocage.lib.JailConfigAddresses
import iocage.lib.JailConfigResolver
import iocage.lib.JailConfigFstab
import iocage.lib.JailConfigLegacy
import iocage.lib.JailConfigZFS
import iocage.lib.helpers

from uuid import UUID

class JailConfig():

  def __init__(self, data = {}, jail=None, logger=None):

    iocage.lib.helpers.init_logger(self, logger)

    object.__setattr__(self, 'data', {})
    object.__setattr__(self, 'special_properties', {})
    object.__setattr__(self, 'legacy', False)

    # jail is required for various operations (write, fstab, etc)
    if jail:
      object.__setattr__(self, 'jail', jail)
      fstab = iocage.lib.JailConfigFstab.JailConfigFstab(jail=jail, logger=self.logger)
      object.__setattr__(self, 'fstab', fstab)
    else:
      self.jail = None
      self.fstab = None

    # the UUID is used in many other variables and needs to be set first
    try:
      self.set_uuid(data.uuid)
    except:
      object.__setattr__(self, 'uuid', None)
      pass

    # be aware of iocage-legacy jails for migration
    try:
      self.legacy = data.legacy == True
    except:
      self.legacy = False

    self.clone(data);

  def clone(self, data):
    for key in data:
      self.__setattr__(key, data[key])

  def read(self):

    try:
      iocage.lib.JailConfigJSON.JailConfigJSON.read(self)
      object.__setattr__(self, 'legacy', False)
      self.logger.log("Configuration loaded from JSON", level="verbose")
      return
    except:
      pass

    try:
      iocage.lib.JailConfigLegacy.JailConfigLegacy.read(self)
      object.__setattr__(self, 'legacy', True)
      self.logger.log("Configuration loaded from UCL config file (iocage-legacy)", level="verbose")
      return
    except:
      pass

    try:
      iocage.lib.JailConfigZFS.JailConfigZFS.read(self)
      object.__setattr__(self, 'legacy', True)
      self.logger.log("Configuration loaded from ZFS properties (iocage-legacy)", level="verbose")
      return
    except:
      pass

    self.logger.log("No configuration was found", level="verbose")

  def update_special_property(self, name, new_property_handler=None):

    if new_property_handler != None:
      self.special_properties[name] = new_property_handler

    self.data[name] = str(self.special_properties[name])

  def _set_name(self, value):

    self.name = value

    try:
      self.host_hostname
    except:
      self.host_hostname = value
      pass

  def save(self):
    if not self.legacy:
      self.save_json()
    else:
      iocage.lib.JailConfigLegacy.JailConfigLegacy.save(self)

  def save_json(self):
    iocage.lib.JailConfigJSON.JailConfigJSON.save(self)

  def set_uuid(self, uuid):
    if isinstance(uuid, str):
      uuid = str(UUID(uuid))
    object.__setattr__(self, 'uuid', uuid)

  def _get_type(self):
    current_type = None

    try:
      if (self.data["type"] == "jail") or (self.data["type"] == ""):
        current_type = "jail"
    except:
      current_type = "jail"

    if current_type == "jail":
      if self.basejail:
        return "basejail"
      elif self.clonejail:
        return "clonejail"
      else:
        return "jail"

    return self.data["type"]

  def _set_type(self, value):

    if value == "basejail":
      self.basejail = True
      self.clonejail = False
      self.data["type"] = "jail"

    elif value == "clonejail":
      self.basejail = False
      self.clonejail = True
      self.data["type"] = "jail"

    else:
      self.data["type"] = value

  def _get_basejail(self):
    return (self.data["basejail"] == "on") or (self.data["basejail"] == "yes") 

  def _default_basejail(self):
    return False

  def _set_basejail(self, value):
    enabled = (value == True) or (value == "on") or (value == "yes")
    if self.legacy:
      self.data["basejail"] = "on" if enabled else "off"
    else:
      self.data["basejail"] = "yes" if enabled else "no"

  def _get_clonejail(self):
    return self.data["clonejail"] == "on"

  def _default_clonejail(self):
    return True

  def _set_clonejail(self, value):
    self.data["clonejail"] = "on" if (value == True) or (value == "on") else "off"

  def _get_ip4_addr(self):
    try:
      return self.special_properties["ip4_addr"]
    except:
      return None
    
  def _set_ip4_addr(self, value):
    self.special_properties["ip4_addr"] = iocage.lib.JailConfigAddresses.JailConfigAddresses(
      value,
      jail_config=self,
      property_name="ip4_addr"
    )
    self.update_special_property("ip4_addr")

  def _get_ip6_addr(self):
    try:
      return self.special_properties["ip6_addr"]
    except:
      return None

  def _set_ip6_addr(self, value):
    self.special_properties["ip6_addr"] = iocage.lib.JailConfigAddresses.JailConfigAddresses(
      value,
      jail_config=self,
      property_name="ip6_addr"
    )
    self.update_special_property("ip6_addr")

  def _get_interfaces(self):
    return self.special_properties["interfaces"]
    
  def _set_interfaces(self, value):
    self.special_properties["interfaces"] = iocage.lib.JailConfigInterfaces.JailConfigInterfaces(value, jail_config=self)
    self.update_special_property("interfaces")

  def _get_defaultrouter(self):
    value = self.data['defaultrouter']
    return value if (value != "none" and value != None) else None

  def _set_defaultrouter(self, value):
    if value == None:
      value = 'none'
    self.data['defaultrouter'] = value

  def _default_defaultrouter(self):
    return "none"

  def _get_defaultrouter6(self):
    value = self.data['defaultrouter6']
    return value if (value != "none" and value != None) else None

  def _set_defaultrouter6(self, value):
    if value == None:
      value = 'none'
    self.data['defaultrouter6'] = value

  def _default_defaultrouter6(self):
    return "none"

  def _get_vnet(self):
    return self.data["vnet"] == "on"

  def _set_vnet(self, value):
    vnet_enabled = (value == "on") or (value == True)
    self.data["vnet"] = "on" if vnet_enabled else "off"

  def _get_jail_zfs_dataset(self):
    try:
      return self.data["jail_zfs_dataset"].split()
    except:
      pass
    return []

  def _set_jail_zfs_dataset(self, value):
    value = [value] if isinstance(value, str) else value
    self.data["jail_zfs_dataset"] = " ".join(value)

  def _get_jail_zfs(self):
    enabled = self.data["jail_zfs"] == "on"
    if not enabled:
      if len(self.jail_zfs_dataset) > 0:
        raise Exception("jail_zfs is disabled despite jail_zfs_dataset is configured")
    return enabled

  def _set_jail_zfs(self, value):
    if (value == None) or (value == ""):
      del self.data["jail_zfs"]
      return
    enabled = (value == "on") or (value == True)
    self.data["jail_zfs"] = "on" if enabled else "off"

  def _default_jail_zfs(self):
    # if self.data["jail_zfs"] does not explicitly exist, _get_jail_zfs would raise
    try:
      return len(self.jail_zfs_dataset) > 0
    except:
      return False

  def _default_mac_prefix(self):
    return "02ff60"

  def _get_resolver(self):
    return self.__create_special_property_resolver()

  def _set_resolver(self, value):
  
    if isinstance(value, str):
      self.data["resolver"] = value
      resolver = self.resolver
    else:
      resolver = iocage.lib.JailConfigResolver.JailConfigResolver(jail_config=self)
      resolver.update(value, notify=True)

  def _get_cloned_release(self):
    try:
      return self.data["cloned_release"]
    except:
      return self.release

  def _get_basejail_type(self):
    return self.data["basejail_type"]

  def _default_basejail_type(self):
    try:
      if self.basejail:
        return "nullfs"
    except:
      pass
    return None

  def _default_vnet(self):
    return False

  def _default_ip4_saddrsel(self):
    return 1

  def _default_ip6_saddrsel(self):
    return 1

  def _default_ip4(self):
    return "new"

  def _default_ip6(self):
    return "new"

  def _default_host_hostname(self):
    return self.jail.humanreadable_name

  def _default_host_hostuuid(self):
    return self.uuid

  def _default_host_domainname(self):
    return "none"

  def _default_devfs_ruleset(self):
    return "4"

  def _default_enforce_statfs(self):
    return "2"

  def _default_children_max(self):
    return "0"

  def _default_allow_set_hostname(self):
    return "1"

  def _default_allow_sysvipc(self):
    return "0"

  def _default_allow_raw_sockets(self):
    return "0"

  def _default_allow_chflags(self):
    return "0"

  def _default_allow_mount(self):
    return "0"

  def _default_allow_mount_devfs(self):
    return "0"

  def _default_allow_mount_nullfs(self):
    return "0"

  def _default_allow_mount_procfs(self):
    return "0"

  def _default_allow_mount_zfs(self):
    return "0"

  def _default_allow_mount_tmpfs(self):
    return "0"

  def _default_allow_quotas(self):
    return "0"

  def _default_allow_socket_af(self):
    return "0"

  def _default_sysvmsg(self):
    return "new"
  
  def _default_sysvsem(self):
    return "new"

  def _default_sysvshm(self):
    return "new"

  def _default_exec_clean(self):
    return "1"

  def _default_exec_fib(self):
    return "0"

  def _default_exec_prestart(self):
    return "/usr/bin/true"

  def _default_exec_start(self):
    return "/bin/sh /etc/rc"

  def _default_exec_poststart(self):
    return "/usr/bin/true"

  def _default_exec_prestop(self):
    return "/usr/bin/true"

  def _default_exec_stop(self):
    return "/bin/sh /etc/rc.shutdown"

  def _default_exec_poststop(self):
    return "/usr/bin/true"

  def _default_exec_timeout(self):
    return "60"

  def _default_stop_timeout(self):
    return "30"

  def _default_mount_devfs(self):
    return "1"

  def _default_mount_fdescfs(self):
    return "1"

  def __create_special_property_resolver(self):
    
    create_new = False
    try:
      self.special_properties["resolver"]
    except:
      create_new = True
      pass

    if create_new:
      resolver = iocage.lib.JailConfigResolver.JailConfigResolver(jail_config=self, logger=self.logger)
      resolver.update(notify=False)
      self.special_properties["resolver"] = resolver

    return self.special_properties["resolver"]

  def __getattr__(self, key):

    # passthrough existing properties
    try:
      return self.__getattribute__(key)
    except:
      pass

    # data with mappings
    get_method = None
    try:
      get_method = self.__getattribute__(f"_get_{key}")
      return get_method()
    except:
      pass

    # plain data attribute
    try:
      return self.data[key]
    except:
      pass

    # then fall back to default
    try:
      fallback_method = self.__getattribute__(f"_default_{key}")
      return fallback_method()
    except:
      raise Exception(f"Variable {key} not found")

  def __setattr__(self, key, value):

    # passthrough existing properties
    try:
      self.__getattribute__(key)
      object.__setattr__(self, key, value)
      return
    except:
      pass

    setter_method = None
    try:
      setter_method = self.__getattribute__(f"_set_{key}")
    except:
      self.data[key] = value
      pass

    if setter_method != None:
      return setter_method(value)

  def __str__(self):
    return iocage.lib.JailConfigJSON.JailConfigJSON.toJSON(self)
