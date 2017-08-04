import iocage.lib.Release
import iocage.lib.helpers

import os
import platform
import re
import libzfs
import urllib.request

class Distribution:

  release_name_blacklist = [
    "",
    ".",
    "..",
    "ISO-IMAGES"
  ]

  mirror_link_pattern = r"a href=\"([A-z0-9\-_\.]+)/\""

  def __init__(self, host, zfs=None):
    iocage.lib.helpers.init_zfs(self, zfs)
    self.host = host
    self.available_releases = None

  @property
  def name(self):
    if os.uname()[2].endswith("-HBSD"):
      return "HardenedBSD"
    else:
      return platform.system()

  @property
  def mirror_url(self):
    
    distribution = self.name
    processor = self.host.processor

    if distribution == "FreeBSD":
      return f"http://ftp.freebsd.org/pub/FreeBSD/releases/{processor}/{processor}"
    elif distribution == "HardenedBSD":
      return f"http://http://jenkins.hardenedbsd.org/builds"
    else:
      raise Exception(f"Unknown Distribution '{distribution}'")

  def fetch_releases(self):
    
    resource = urllib.request.urlopen(self.mirror_url)
    charset = resource.headers.get_content_charset()
    response = resource.read().decode(charset if charset else "UTF-8")
    
    available_releases = list(map(lambda x: iocage.lib.Release.Release(
        name=x,
        host=self.host,
        zfs=self.zfs
      ),
      filter(lambda y: y not in Distribution.release_name_blacklist,
        map(lambda z: z.strip("\"/"),
          re.findall(Distribution.mirror_link_pattern, response, re.MULTILINE)
        )
      )
    ))

    self.available_releases = available_releases
    return available_releases

  @property
  def releases(self):
    if not self.available_releases:
      self.fetch_releases()
    return self.available_releases
