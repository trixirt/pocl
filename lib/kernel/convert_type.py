#!/usr/bin/env python
# -*- coding: utf8 -*- 

# OpenCL built-in library: type conversion functions
#
# Copyright (c) 2013 Victor Oliveira <victormatheus@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# this code generates the file convert_type.cl, which contains all opencl functions in
# the form:
# convert_destTypen<_sat><_roundingMode>(sourceTypen)

# SRC and DST must be scalars
convert_scalar = """
  %(DST)s _cl_overloadable convert_%(DST)s(%(SRC)s a)
  {
    return (%(DST)s)a;
  }
"""

# implementing vector SRC and DST in terms of scalars
convert_half = """
  %(DST)s%(DSTSIZE)s _cl_overloadable convert_%(DST)s%(DSTSIZE)s(%(SRC)s%(SRCSIZE)s a)
  {
    return (%(DST)s%(DSTSIZE)s)(convert_%(DST)s%(HALFSIZE)s(a.lo), convert_%(DST)s%(HALFSIZE)s(a.hi));
  }
"""

convert_012 = """
  %(DST)s3 _cl_overloadable convert_%(DST)s3(%(SRC)s3 a)
  {
    return (%(DST)s3)(convert_%(DST)s2(a.s01), convert_%(DST)s(a.s2));
  }
"""

types = ['char', 'uchar', 'short', 'ushort', 'int', 'uint', 'long', 'ulong', 'float', 'double']

int_types = ['char', 'uchar', 'short', 'ushort', 'int', 'uint', 'long', 'ulong']
float_types = ['float', 'double']

int64_types = ['long', 'ulong']
float64_types = ['double']

vector_sizes = ['', '2', '4', '8', '16']
saturated = ['','sat']
ieee_modes = ['rte','rtz','rtp','rtn']

half_sizes = [('2','2',''), ('4','4','2'), ('8','8','4'), ('16', '16', '8')]

print """
#include "templates.h"

void cl_set_rounding_mode(int mode);
void cl_set_default_rounding_mode();
"""

def guards(src, dst):
  if src in int64_types or dst in int64_types:
    print """__IF_INT64("""
    return True
  if src in float64_types or dst in float64_types:
    print """__IF_FP64("""
    return True
  return False


for src in types:
  for dst in types:
    must_close = guards(src, dst)

    print convert_scalar % {'SRC':src, 'DST':dst}

    for src_size, dst_size, halfdst_size in half_sizes:
      print convert_half % {'SRC':src, 'SRCSIZE':src_size, 'DST':dst, 'DSTSIZE':dst_size, 'HALFSIZE':halfdst_size}

    print convert_012 % {'SRC':src, 'DST':dst}

    if must_close: print """)"""

#saturated conversions

for src in types:
  for dst in int_types:
    must_close = guards(src, dst)
    for size in vector_sizes:
      # SRC and DST may be vectors
      print  """  %(DST)s%(SIZE)s _cl_overloadable
  convert_%(DST)s%(SIZE)s_sat(%(SRC)s%(SIZE)s a)
  {
    int const src_size = sizeof(%(SRC)s);
    int const dst_size = sizeof(%(DST)s);""" % {'SRC':src, 'DST':dst, 'SIZE':size}
      
      if src == 'float':
        if dst[0] == 'u':
          print """    %(DST)s const DST_MAX = (%(DST)s)0 - (%(DST)s)1;
    return (convert_%(DST)s%(SIZE)s(a > (%(SRC)s)DST_MAX) ? (%(DST)s%(SIZE)s)DST_MAX :
            convert_%(DST)s%(SIZE)s(a));""" % {'SRC':src, 'DST':dst, 'SIZE':size}
        else:
          print """    %(DST)s const DST_MIN = (%(DST)s)1 << (%(DST)s)(CHAR_BIT * dst_size - 1);
    %(DST)s const DST_MAX = DST_MIN - (%(DST)s)1;
    return (convert_%(DST)s%(SIZE)s(a < (%(SRC)s)DST_MIN) ? (%(DST)s%(SIZE)s)DST_MIN :
            convert_%(DST)s%(SIZE)s(a > (%(SRC)s)DST_MAX) ? (%(DST)s%(SIZE)s)DST_MAX :
            convert_%(DST)s%(SIZE)s(a));""" % {'SRC':src, 'DST':dst, 'SIZE':size}
      elif src[0] == 'u':
        if dst[0] == 'u':
          print """    if (dst_size >= src_size) return convert_%(DST)s%(SIZE)s(a);
    %(DST)s const DST_MAX = (%(DST)s)0 - (%(DST)s)1;
    return (convert_%(DST)s%(SIZE)s(a > (%(SRC)s)DST_MAX) ? (%(DST)s%(SIZE)s)DST_MAX :
            convert_%(DST)s%(SIZE)s(a));""" % {'SRC':src, 'DST':dst, 'SIZE':size}
        else:
          print """    if (dst_size > src_size) return convert_%(DST)s%(SIZE)s(a);
    %(DST)s const DST_MAX = (%(DST)s)1 << (%(DST)s)(CHAR_BIT * dst_size);
    return (convert_%(DST)s%(SIZE)s(a > (%(SRC)s)DST_MAX) ? (%(DST)s%(SIZE)s)DST_MAX :
            convert_%(DST)s%(SIZE)s(a));""" % {'SRC':src, 'DST':dst, 'SIZE':size}
      else:
        if dst[0] == 'u':
          print """    if (dst_size >= src_size) {
      return (convert_%(DST)s%(SIZE)s(a < (%(SRC)s)0) ? (%(DST)s%(SIZE)s)0 :
              convert_%(DST)s%(SIZE)s(a));
    }
    %(DST)s const DST_MAX = (%(DST)s)0 - (%(DST)s)1;
    return (convert_%(DST)s%(SIZE)s(a < (%(SRC)s)0      ) ? (%(DST)s%(SIZE)s)0 :
            convert_%(DST)s%(SIZE)s(a > (%(SRC)s)DST_MAX) ? (%(DST)s%(SIZE)s)DST_MAX :
            convert_%(DST)s%(SIZE)s(a));""" % {'SRC':src, 'DST':dst, 'SIZE':size}
        else:
          print """    if (dst_size >= src_size) return convert_%(DST)s%(SIZE)s(a);
    %(DST)s const DST_MIN = (%(DST)s)1 << (%(DST)s)(CHAR_BIT * dst_size - 1);
    %(DST)s const DST_MAX = DST_MIN - (%(DST)s)1;
    return (convert_%(DST)s%(SIZE)s(a < (%(SRC)s)DST_MIN) ? (%(DST)s%(SIZE)s)DST_MIN :
            convert_%(DST)s%(SIZE)s(a > (%(SRC)s)DST_MAX) ? (%(DST)s%(SIZE)s)DST_MAX :
            convert_%(DST)s%(SIZE)s(a));""" % {'SRC':src, 'DST':dst, 'SIZE':size}
      
      print """  }
    """
    if must_close: print """)"""

def convert_rm(src, dst, size, rm, sat):
  must_close = guards(src, dst)
  print """  %(DST)s%(SIZE)s _cl_overloadable""" % {'DST':dst, 'SIZE':size}
  
  if sat:
    print """  convert_%(DST)s%(SIZE)s_sat_%(RM)s(%(SRC)s%(SIZE)s a)""" % {'SRC':src, 'DST':dst, 'SIZE':size, 'RM':rm}

  else:
    print """  convert_%(DST)s%(SIZE)s_%(RM)s(%(SRC)s%(SIZE)s a)""" % {'SRC':src, 'DST':dst, 'SIZE':size, 'RM':rm}
  
  print """  {"""
  
  fmode = {'rtz' : '0',
           'rte' : '1',
           'rtp' : '2',
           'rtn' : '3'}
  
  print """    cl_set_rounding_mode(%s);""" % fmode[rm]
  
  if sat:
    print """    %(DST)s%(SIZE)s result = convert_%(DST)s%(SIZE)s_sat(a);""" % {'DST':dst, 'SIZE':size}
  else:
    print """    %(DST)s%(SIZE)s result = convert_%(DST)s%(SIZE)s(a);""" % {'DST':dst, 'SIZE':size}
  
  # set default floating-point policy
  print """    cl_set_default_rounding_mode();
    return result;
  }
  """

  if must_close: print """)"""

# only functions that work on floating-point types should care about rounding modes
# only functions that target integer types should care about saturation

for src in float_types:
  for dst in int_types:
    for size in vector_sizes:
      for rm in ieee_modes:
        for sat in ['', 'sat']:
          convert_rm(src, dst, size, rm, sat)

for src in int_types:
  for dst in float_types:
    for size in vector_sizes:
      for rm in ieee_modes:
        convert_rm(src, dst, size, rm, '')
