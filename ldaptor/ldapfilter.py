#!/usr/bin/python

from ldaptor.protocols import pureldap

"""

RFC2254:

	filter     = "(" filtercomp ")"
	filtercomp = and / or / not / item
	and        = "&" filterlist
	or         = "|" filterlist
	not        = "!" filter
	filterlist = 1*filter
	item       = simple / present / substring / extensible
	simple     = attr filtertype value
	filtertype = equal / approx / greater / less
	equal      = "="
	approx     = "~="
	greater    = ">="
	less       = "<="
	extensible = attr [":dn"] [":" matchingrule] ":=" value
		     / [":dn"] ":" matchingrule ":=" value
	present    = attr "=*"
	substring  = attr "=" [initial] any [final]
	initial    = value
	any        = "*" *(value "*")
	final      = value
	attr       = AttributeDescription from Section 4.1.5 of [1]
	matchingrule = MatchingRuleId from Section 4.1.9 of [1]
	value      = AttributeValue from Section 4.1.6 of [1]
"""

class InvalidLDAPFilter(Exception):
    def __init__(self, msg, loc, text):
	Exception.__init__(self)
	self.msg=msg
	self.loc=loc
	self.text=text

    def __str__(self):
	return "Invalid LDAP filter: %s at point %d in %r" \
	       % (self.msg, self.loc, self.text)

def parseExtensible(attr, s):
    raise NotImplementedError

from pyparsing import Word, Literal, Optional, ZeroOrMore, Suppress, \
                       Group, Forward, OneOrMore, ParseException, \
                       CharsNotIn, Combine, empty, StringStart, \
                       StringEnd

import copy, string

filter_ = Forward()
attr = Word('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789;-',)
attr.leaveWhitespace()
escaped = Suppress(Literal('\\'))+Word(string.hexdigits, exact=2)
def _p_escaped(s,l,t):
    text=t[0]
    return chr(int(text, 16))
escaped.setParseAction(_p_escaped)
value = Combine(OneOrMore(CharsNotIn('*()\\\0') | escaped))
equal = Literal("=")
equal.setParseAction(lambda s,l,t: pureldap.LDAPFilter_equalityMatch)
approx = Literal("~=")
approx.setParseAction(lambda s,l,t: pureldap.LDAPFilter_approxMatch)
greater = Literal(">=")
greater.setParseAction(lambda s,l,t: pureldap.LDAPFilter_greaterOrEqual)
less = Literal("<=")
less.setParseAction(lambda s,l,t: pureldap.LDAPFilter_lessOrEqual)
filtertype = equal | approx | greater | less
simple = attr + filtertype + value
simple.leaveWhitespace()
def _p_simple(s,l,t):
    attr, filtertype, value = t
    return filtertype(attributeDesc=pureldap.LDAPAttributeDescription(attr),
                      assertionValue=pureldap.LDAPAssertionValue(value))
simple.setParseAction(_p_simple)
present = attr + "=*"
present.setParseAction(lambda s,l,t: pureldap.LDAPFilter_present(t[0]))
initial = copy.copy(value)
initial.setParseAction(lambda s,l,t: pureldap.LDAPFilter_substrings_initial(t[0]))
any_value = value + Suppress(Literal("*"))
any_value.setParseAction(lambda s,l,t: pureldap.LDAPFilter_substrings_any(t[0]))
any = Suppress(Literal("*")) + ZeroOrMore(any_value)
final = copy.copy(value)
final.setParseAction(lambda s,l,t: pureldap.LDAPFilter_substrings_final(t[0]))
substring = attr + Suppress(Literal("=")) + Group(Optional(initial) + any + Optional(final))
def _p_substring(s,l,t):
    attrtype, substrings = t
    return pureldap.LDAPFilter_substrings(
        type=attrtype,
        substrings=substrings)
substring.setParseAction(_p_substring)

keystring = Word('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
                 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789;-')
numericoid = Combine(Word('0123456789') + ZeroOrMore(Literal('.') + Word('0123456789')))
oid = numericoid | keystring
matchingrule = copy.copy(oid)

extensible_dn = Optional(":dn")
def _p_extensible_dn(s,l,t):
    return not not t
extensible_dn.setParseAction(_p_extensible_dn)

matchingrule_or_none = Optional(Suppress(":") + matchingrule)
def _p_matchingrule_or_none(s,l,t):
    if not t:
        return [None]
    else:
        return t[0]
matchingrule_or_none.setParseAction(_p_matchingrule_or_none)

extensible_attr = attr + extensible_dn + matchingrule_or_none + Suppress(":=") + value
def _p_extensible_attr(s,l,t):
    return list(t)
extensible_attr.setParseAction(_p_extensible_attr)


extensible_noattr = extensible_dn + Suppress(":") + matchingrule + Suppress(":=") + value
def _p_extensible_noattr(s,l,t):
    return [None]+list(t)
extensible_noattr.setParseAction(_p_extensible_noattr)

extensible = extensible_attr | extensible_noattr
def _p_extensible(s,l,t):
    attr, dn, matchingRule, value = t
    return pureldap.LDAPFilter_extensibleMatch(
        matchingRule=matchingRule,
        type=attr,
        matchValue=value,
        dnAttributes=dn)
extensible.setParseAction(_p_extensible)
item = simple ^ present ^ substring ^ extensible
item.leaveWhitespace()
not_ = Suppress(Literal('!')) + filter_
not_.setParseAction(lambda s,l,t: pureldap.LDAPFilter_not(t[0]))
filterlist = OneOrMore(filter_)
or_ = Suppress(Literal('|')) + filterlist
or_.setParseAction(lambda s,l,t: pureldap.LDAPFilter_or(t))
and_ = Suppress(Literal('&')) + filterlist
and_.setParseAction(lambda s,l,t: pureldap.LDAPFilter_and(t))
filtercomp = and_ | or_ | not_ | item
filter_ << (Suppress(Literal('(').leaveWhitespace())
            + filtercomp
            + Suppress(Literal(')').leaveWhitespace()))
filtercomp.leaveWhitespace()
filter_.leaveWhitespace()

toplevel = (StringStart().leaveWhitespace()
            + filter_
            + StringEnd().leaveWhitespace())
toplevel.leaveWhitespace()

def parseFilter(s):
    try:
        x=toplevel.parseString(s)
    except ParseException, e:
        raise InvalidLDAPFilter, (e.msg,
                                  e.loc,
                                  e.line)
    assert len(x)==1
    return x[0]

if __name__=='__main__':
    import sys
    for filt in sys.argv[1:]:
	print repr(parseFilter(filt))
        print
