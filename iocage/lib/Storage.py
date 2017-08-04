from iocage.lib.Command import Command

import libzfs
import pwd
import grp
import os


class Storage:

  def __init__(self, jail, zfs=None, auto_create=False, safe_mode=True, fsopts={}):

    if isinstance(zfs, libzfs.ZFS):
      self.zfs = zfs
    else:
      self.zfs = libzfs.ZFS(history=True, history_prefix="<iocage>")

    self.jail = jail

    # when auto_create is enabled, non-existing zfs volumes will be automatically created
    # if not enabled, accessing non-existent datasets will raise an error
    self.auto_create = auto_create

    # safe-mody only attaches zfs datasets to jails that were tagged with jailed=on already exist
    self.safe_mode = safe_mode

    # additional fsopts
    self._set_fsopts(fsopts)

  @property
  def zfs_enabled(self):
    try:
      return self.jail.config.jail_zfs == True
    except:
      return False

  @property
  def zfs_datasets(self):
    return self.get_zfs_datasets(self.auto_create)

  def get_zfs_datasets(self, auto_create=None):
    dataset_names = self.jail.config.jail_zfs_dataset
    dataset_not_found_error = False

    auto_create = self.auto_create if auto_create == None else auto_create

    datasets = set()
    for name in dataset_names:

      zpool = None
      try:
        zpool = self._get_zpool_from_dataset_name(name)
      except:
        pass

      try:
        # legacy support (datasets not prefixed with pool/)
        zpool = self._get_zpool_from_dataset_name(f"{self.jail.zfs_pool_name}/{name}")
        name = f"{self.jail.zfs_pool_name}/{name}"
      except:

        pass

      try:
        if auto_create:
          zpool.create(name, self.fsopts, create_ancestors=True)
      except Exception as e:
        print(e)
        pass
      
      try:
        dataset = self.zfs.get_dataset(name)
        datasets.add(dataset);
      except:
        raise Exception(f"Neither the dataset {name} nor {self.jail.zfs_pool_name}/{name} could be found")

    return datasets

  def apply(self, auto_create=False):
    if self.zfs_enabled:
      self._mount_procfs()
      self._mount_jail_datasets(auto_create=auto_create)

  def umount_nullfs(self):

    with open(f"{self.jail.path}/fstab") as f:
      mounts = []
      for mount in f.read().splitlines():
        try:
          mounts.append(mount.replace("\t", " ").split(" ")[1])
        except:
          pass

      if (len(mounts) > 0):
        Command.exec(Command, ["umount"] + mounts)

  def _require_datasets_exist_and_jailed(self):
    existing_datasets = self.get_zfs_datasets(auto_create=False)
    for existing_dataset in existing_datasets:
        if existing_dataset.properties["jailed"] != "on":
          raise("Dataset {existing_dataset.name} is not jailed. Run 'zfs set jailed=on {existing_dataset.name}' to allow mounting")

  def _mount_jail_datasets(self, auto_create=None):
    
    auto_create = self.auto_create if auto_create == None else (auto_create == True)

    if self.safe_mode:
      self._require_datasets_exist_and_jailed()

    for dataset in self.zfs_datasets:

      self._unmount_local(dataset);

      # ToDo: bake jail feature into py-libzfs
      Command.exec(Command, ["zfs", "jail", self.jail.identifier, dataset.name])

      if dataset.properties['mountpoint']:
        for child in list(dataset.children):
          self._ensure_dataset_exists(child)
          self._mount_jail_dataset(child.name)

  def _mount_procfs(self):
    try:
      if jail.config.mount_procfs:
        Command.exec(Command, [
          "mount"
          "-t",
          "procfs"
          "proc"
          f"{self.path}/root/proc"
        ])
        print("procfs mounted")
    except:
      pass

  def _mount_linprocfs(self):
    try:
      if not jail.config.mount_linprocfs:
        return
    except:
      pass

    linproc_path = "compat/linux/proc"
    self._jail_mkdirp(f"{self.path}/root/{linproc_path}")

    try:
      if jail.config.mount_procfs:
        Command.exec(Command, [
          "mount"
          "-t",
          "linprocfs"
          "linproc"
          f"{self.path}/root/{linproc_path}"
        ])
        print("procfs mounted")
    except:
      pass

  def _mount_jail_dataset(self, dataset_name):
    print(f"mounting {dataset_name}")
    self.jail.exec(['zfs', 'mount', dataset_name])

  def _get_zpool_name_from_dataset_name(self, dataset_name):
    return dataset_name.split("/", maxsplit=1)[0]

  def _get_zpool_from_dataset_name(self, dataset_name):
    target_pool_name = self._get_zpool_name_from_dataset_name(dataset_name)
    for zpool in list(self.zfs.pools):
      if zpool.name == target_pool_name:
        return zpool
    raise Exception(f"zpool {target_pool_name} does not exist")

  def _unmount_local(self, dataset):
    if dataset.mountpoint:
      dataset.unmount()

  def _jail_mkdirp(self, directory, permissions=0o775, user="root", group="wheel"):
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid
    folder = f"{self.jail.path}/{directory}"
    if not os.path.isdir(folder):
      os.mkdirs(folder, permissions)
      os.chown(folder, uid, gid, follow_symlinks=False)

  def _set_fsopts(self, fsopts):
    self.fsopts = fsopts

    default_fsopts = {
      "compression": "lz4"
    }

    for key in default_fsopts:
      try:
        self.fsopts[key]
      except:
        self.fsopts[key] = default_fsopts[key]
