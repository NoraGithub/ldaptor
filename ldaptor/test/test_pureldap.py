# Ldaptor -- TODO
# Copyright (C) 2001 Matthew W. Lefkowitz
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""
Test cases for ldaptor.protocols.pureldap module.
"""

from twisted.trial import unittest
from ldaptor.protocols import pureldap, pureber
from ldaptor.mutablestring import MutableString
import types

def s(*l):
    """Join all members of list to a string. Integer members are chr()ed"""
    r=''
    for e in l:
	if isinstance(e, types.IntType):
	    e=chr(e)
	r=r+str(e)
    return r

def l(s):
    """Split a string to ord's of chars."""
    return map(lambda x: ord(x), s)

class KnownValues(unittest.TestCase):
    knownValues=( # class, args, kwargs, expected_result

	(pureldap.LDAPModification_delete,
	 [],
         { "attributeType": 'bar',
	   },
	 [0x30, 0x0c]
	 + [0x0a, 0x01, 0x01]
         + [0x30, 0x07]
	 + [0x04, 0x03] + l("bar")
	 + [0x31, 0x00]),

	(pureldap.LDAPModifyRequest,
	 [],
	 { "object": 'cn=foo, dc=example, dc=com',
	   "modification": [pureldap.LDAPModification_delete('bar')]
	   },
	 [0x66, 0x2c]
	 + [0x04, 0x1a]
	 + l("cn=foo, dc=example, dc=com")
	 + [0x30, 0x0e]
	 + [0x30, 0x0c]
	 + [0x0a, 0x01, 0x01]
	 + [0x30, 0x07]
	 + [0x04, 0x03] + l("bar")
	 + [0x31, 0x00]),

	(pureldap.LDAPFilter_not,
	 [],
	 { "value": pureldap.LDAPFilter_present("foo"),
	   },
	 [0xa2, 0x05]
	 + [0x87]
	 + [len("foo")]
	 + l("foo")),

	(pureldap.LDAPModifyDNRequest,
	 [],
	 {'entry': 'cn=foo,dc=example,dc=com',
	  'newrdn': 'uid=bar',
	  'deleteoldrdn': 0,
	  },
	 [0x6c, 0x26]
	 + [0x04]
	 + [len("cn=foo,dc=example,dc=com")]
	 + l("cn=foo,dc=example,dc=com")
	 + [0x04]
	 + [len("uid=bar")]
	 + l("uid=bar")
	 + [0x01, 0x01, 0x00]),

	(pureldap.LDAPModifyDNRequest,
	 [],
	 {'entry': 'cn=aoue,dc=example,dc=com',
	  'newrdn': 'canonname=aoue',
	  'deleteoldrdn': 0,
	  'newSuperior': 'ou=People,dc=example,dc=com',
	  },
	 [0x6c, 0x4b]
	 + [0x04]
	 + [len("cn=aoue,dc=example,dc=com")]
	 + l("cn=aoue,dc=example,dc=com")
	 + [0x04]
	 + [len("canonname=aoue")]
	 + l("canonname=aoue")
	 + [0x01, 0x01, 0x00]
	 + [0x80]
	 + [len("ou=People,dc=example,dc=com")]
	 + l("ou=People,dc=example,dc=com")),

        (pureldap.LDAPSearchRequest,
         [],
         {'baseObject': 'dc=yoja,dc=example,dc=com',
          },
         [0x63, 57]
         + [0x04]
         + [len('dc=yoja,dc=example,dc=com')]
         + l('dc=yoja,dc=example,dc=com')
         # scope
         + [0x0a, 1, 2]
         # derefAliases
         + [0x0a, 1, 0]
         # sizeLimit
         + [0x02, 1, 0]
         # timeLimit
         + [0x02, 1, 0]
         # typesOnly
         + [0x01, 1, 0]
         # filter
         + [135, 11] + l('objectClass')
         # attributes
         + [48, 0]
         ),

        (pureldap.LDAPUnbindRequest,
         [],
         {},
         [0x42, 0x00]
	),

        (pureldap.LDAPSearchResultDone,
         [],
         {'resultCode': 0,
          },
         [0x65, 0x07]
         # resultCode
         + [0x0a, 0x01, 0x00]
         # matchedDN
         + [0x04]
         + [len('')]
         + l('')
         # errorMessage
         + [0x04]
         + [len('')]
         + l('')
         # referral, TODO
         + []
	),

        (pureldap.LDAPSearchResultDone,
         [],
         {'resultCode': 0,
          'matchedDN': 'dc=foo,dc=example,dc=com',
          },
         [0x65, 31]
         # resultCode
         + [0x0a, 0x01, 0x00]
         # matchedDN
         + [0x04]
         + [len('dc=foo,dc=example,dc=com')]
         + l('dc=foo,dc=example,dc=com')
         # errorMessage
         + [0x04]
         + [len('')]
         + l('')
         # referral, TODO
         + []
	),

        (pureldap.LDAPSearchResultDone,
         [],
         {'resultCode': 0,
          'matchedDN': 'dc=foo,dc=example,dc=com',
          'errorMessage': 'the foobar was fubar',
          },
         [0x65, 51]
         # resultCode
         + [0x0a, 0x01, 0x00]
         # matchedDN
         + [0x04]
         + [len('dc=foo,dc=example,dc=com')]
         + l('dc=foo,dc=example,dc=com')
         # errorMessage
         + [0x04]
         + [len('the foobar was fubar')]
         + l('the foobar was fubar',)
         # referral, TODO
         + []
	),

        (pureldap.LDAPSearchResultDone,
         [],
         {'resultCode': 0,
          'errorMessage': 'the foobar was fubar',
          },
         [0x65, 27]
         # resultCode
         + [0x0a, 0x01, 0x00]
         # matchedDN
         + [0x04]
         + [len('')]
         + l('')
         # errorMessage
         + [0x04]
         + [len('the foobar was fubar')]
         + l('the foobar was fubar',)
         # referral, TODO
         + []
	),

        )

    def testToLDAP(self):
	"""str(LDAPClass(...)) should give known result with known input"""
	for klass, args, kwargs, encoded in self.knownValues:
	    result = klass(*args, **kwargs)
	    result = str(result)
	    result = map(ord, result)
	    if result!=encoded:
		raise AssertionError, \
		      "Class %s(*%s, **%s) doesn't encode properly: " \
		      "%s != %s" % (klass.__name__,
				    repr(args), repr(kwargs),
				    repr(result), repr(encoded))

    def testFromLDAP(self):
	"""LDAPClass(encoded="...") should give known result with known input"""
	for klass, args, kwargs, encoded in self.knownValues:
	    m=MutableString(s(*encoded))
	    m.append('foo')
	    result = klass(encoded=m, berdecoder=pureber.BERDecoderContext())
	    assert m=='foo'

	    shouldBe = klass(*args, **kwargs)
	    #TODO shouldn't use str below
	    assert str(result)==str(shouldBe), \
		   "Class %s(*%s, **%s) doesn't decode properly: " \
		   "%s != %s" % (klass.__name__,
				 repr(args), repr(kwargs),
				 repr(result), repr(shouldBe))

    def testPartial(self):
	"""LDAPClass(encoded="...") with too short input should throw BERExceptionInsufficientData"""
	for klass, args, kwargs, encoded in self.knownValues:
	    for i in xrange(len(encoded)):
		m=MutableString(s(*encoded))[:i]
		self.assertRaises(pureber.BERExceptionInsufficientData,
				  klass,
				  encoded=m,
				  berdecoder=pureber.BERDecoderContext())

    def testPartialLDAPModifyRequestEncodings_old(self):
	"""LDAPModifyRequest(encoded="...") with too short input should throw BERExceptionInsufficientData"""
	m=str(pureldap.LDAPModifyRequest(object='foo', modification=[pureldap.LDAPModification_delete('bar')]))
	for i in xrange(len(m)):
	    self.assertRaises(pureber.BERExceptionInsufficientData, pureldap.LDAPModifyRequest, encoded=m[:i], berdecoder=pureber.BERDecoderContext())

class TestEquality(unittest.TestCase):
    valuesToTest=(
        (pureldap.LDAPFilter_equalityMatch,
         [ pureldap.LDAPAttributeDescription(value='cn'),
           pureldap.LDAPAssertionValue(value='foo'),
           ]),
        (pureldap.LDAPFilter_equalityMatch,
         [ pureldap.LDAPAttributeDescription(value='cn'),
           pureldap.LDAPAssertionValue(value='bar'),
           ]),
	(pureber.BERInteger, [0]),
	)

    def testEquality(self):
	"""LDAP objects equal LDAP objects with same type and content"""
	for class_, args in self.valuesToTest:
	    x=class_(*args)
	    y=class_(*args)
	    self.assertEquals(x, x)
	    self.assertEquals(x, y)

    def testInEquality(self):
	"""LDAP objects do not equal LDAP objects with different type or content"""
	for i in xrange(len(self.valuesToTest)):
	    for j in xrange(len(self.valuesToTest)):
		if i!=j:
		    i_class, i_args = self.valuesToTest[i]
		    j_class, j_args = self.valuesToTest[j]
		    x=i_class(*i_args)
		    y=j_class(*j_args)
		    self.assertNotEquals(x, y)
