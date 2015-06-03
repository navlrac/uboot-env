#!/usr/bin/python
#
# Copyright (c) 2010 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from optparse import OptionParser
import binascii
import struct
import sys

# This script allows listing, reading and writing environment variables for
# u-boot, that usually live in an area of a block device (NVRAM, e.g. NAND or
# NOR flash).
# The u-boot environment variable area is a crc (4 bytes) followed by all
# environment variables as "key=value" strings (\0-terminated) with \0\0
# (empty string) to indicate the end.


class SizeError(Exception):
  pass


def ReadEnviron(file, size=0, offset=0, nocrc=False, text=False):
  """Reads the u-boot environment variables from a file into a dict."""
  f = open(file, "rb")
  f.seek(offset)
  if size:
    data = f.read(size)
  else:
    data = f.read()
  f.close()

  if not nocrc:
    (crc,) = struct.unpack("I", data[0:4])
    real_data = data[4:]
  else:
    real_data = data[:]
    crc = 0
  real_crc = binascii.crc32(real_data) & 0xffffffff
  environ = {}
  if text:
      delim='\n'
  else:
      delim='\0'
  for s in real_data.split(delim):
    if not s:
      break
    key, value = s.split('=', 1)
    environ[key] = value

  return (environ, len(data), crc == real_crc)

def WriteEnviron(file, environ, size, offset=0, force=False):
  """Writes the u-boot environment variables from a dict into a file."""
  strings = ['%s=%s' % (k, environ[k]) for k in environ]
  data = '\0'.join(strings + [''])

  if force and not size:
    size = len(data)+4

  # pad with \0
  if len(data) <= size-4:
    data = data + '\0'*(size-len(data)-4)
  else:
    raise SizeError

  crc = binascii.crc32(data) & 0xffffffff

  f = open(file, "wb")
  if offset:
    f.seek(offset)
  f.write(struct.pack("I", crc)[0:4])
  f.write(data)
  f.close()


def main(argv):
  parser = OptionParser()
  parser.add_option('-f', '--file', type='string', dest='filename')
  parser.add_option('-o', '--offset', type='int', dest='offset', default=0)
  parser.add_option('-s', '--size', type='int', dest='size', default=0)
  parser.add_option('--out', type='string', dest='out_filename')
  parser.add_option('--out-offset', type='string', dest='out_offset')
  parser.add_option('--out-size', type='int', dest='out_size')
  parser.add_option('--list', action='store_true', dest='list')
  parser.add_option('--force', action='store_true', dest='force')
  parser.add_option('--text', action='store_true', dest='text')
  parser.add_option('--add-crc', action='store_true', dest='nocrc')
  parser.add_option('--get', type='string', action='append', dest='get',
                    default=[])
  parser.add_option('--set', type='string', action='append', dest='set',
                    default=[])
  (options, args) = parser.parse_args()
  (environ, size, crc) = ReadEnviron(options.filename, options.size,
                                     options.offset, options.nocrc,
                                     options.text)
  if not options.nocrc and not crc:
    sys.stderr.write('Bad CRC\n')
    if not options.force:
      sys.exit(1)

  if options.list:
    for key in environ:
      print "%s=%s" % (key, environ[key])

  for key in options.get:
    try:
      print environ[key]
    except KeyError:
      print ''

  do_write = False
  for key_value in options.set:
    key, value = key_value.split('=', 1)
    environ[key] = value
    do_write = True

  if do_write or options.out_filename:
    out_filename = options.out_filename
    out_offset = options.out_offset
    out_size = options.out_size
    if not out_filename:
      out_filename = options.filename
      out_offset = options.offset
      out_size = size
    WriteEnviron(out_filename, environ, out_size, out_offset,
            options.force or options.nocrc)


if __name__ == '__main__':
  main(sys.argv)
