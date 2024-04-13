# Relevant documentation:
# https://www.w3.org/TR/1999/REC-xpath-19991116
# https://github.com/we-like-parsers/pegen
# https://we-like-parsers.github.io/pegen

@subheader'''
def assign(obj, **kwargs):
	for k, v in kwargs.items():
		assert hasattr(obj, k), "%r has no attr %r" % (obj, k)
		setattr(obj, k, v)
	return obj

class Path:

	def __init__(self):
		self.steps = []
		self.absolute = False

	def append(self, step):
		self.steps.append(step)
		return self

	def prepend(self, step):
		self.steps.insert(0, step)
		return self

	def __repr__(self):
		return "Path(absolute=%r, steps=%r)" % (self.absolute, self.steps)

class Step:

	def __init__(self):
		self.axis = "child"
		self.name_test = None
		self.predicates = []

	def __repr__(self):
		return "Step(axis=%r, name_test=%r, predicates=%r)" % (self.axis, self.name_test, self.predicates)

class Op:

	def __init__(self, val, l, r):
		self.val = val
		self.l = l
		self.r = r

	def __repr__(self):
		return "Op(%r, %r, %r)" % (self.val, self.l, self.r)

class Func:

	def __init__(self, name, args):
		self.name = name
		self.args = args

	def __repr__(self):
		return "Func(%r, %r)" % (self.name, self.args)
'''

start: r=LocationPath $ { r }

LocationPath:
	| RelativeLocationPath
	| r=AbsoluteLocationPath { assign(r, absolute=True) }

AbsoluteLocationPath:
	| AbbreviatedAbsoluteLocationPath
	| '/' r=RelativeLocationPath? { r or Path() }

RelativeLocationPath:
	| AbbreviatedRelativeLocationPath
	| r=RelativeLocationPath '/' s=Step { r.append(s) }
	| r=Step { Path().append(r) }

AbbreviatedAbsoluteLocationPath: '//' r=RelativeLocationPath {
	r.prepend(assign(Step(), axis="descendant-or-self")) }
AbbreviatedRelativeLocationPath: r=RelativeLocationPath '//' s=Step {
	r.append(assign(Step(), axis="descendant-or-self")).append(s) }
AbbreviatedStep:
	| '.' '.' { assign(Step(), axis="parent") }
	| '.' { assign(Step(), axis="self") }

Step:
	| q=AxisSpecifier? r=NodeTest s=Predicate* {
		assign(r, axis=q or "child", predicates=s) }
	| r=AbbreviatedStep { r }
AxisSpecifier: r=AxisName ':' ':' { r.string }
AxisName:
	| "ancestor-or-self"
	| "ancestor"
	| "child"
	| "descendant-or-self"
	| "descendant"
	| "following-sibling"
	| "parent"
	| "preceding-sibling"
	| "self"

NodeTest: NameTest

NameTest:
	| '*' { Step() }
	| r=NAME { assign(Step(), name_test=r.string) }

Predicate: '[' r=PredicateExpr ']' { r }
PredicateExpr: Expr

Expr: OrExpr
PrimaryExpr:
	| '(' r=Expr ')' { r }
	| Literal
	| FunctionCall
	| '@' r=NAME { f"(node[{r.string!r}])" }

OrExpr:
	| r=OrExpr "or" s=AndExpr { Op("or", r, s) }
	| AndExpr
AndExpr:
	| r=AndExpr "and" s=NotExpr { Op("and", r, s) }
	| NotExpr
# The xpath spec defines 'not' as a function, but we make it an operator.
# Thus both foo[not(kid)] and foo[not kid] can be used and are equivalent.
NotExpr:
	| "not" r=NotExpr { Op("not", None, r) }
	| EqualityExpr
EqualityExpr:
	| r=EqualityExpr '=' s=RelationalExpr { Op("==", r, s) }
	| r=EqualityExpr '!=' s=RelationalExpr { Op("!=", r, s)}
	| RelationalExpr
RelationalExpr:
	| r=RelationalExpr '<' s=AdditiveExpr { Op("<", r, s) }
	| r=RelationalExpr '>' s=AdditiveExpr { Op(">", r, s) }
	| r=RelationalExpr '<=' s=AdditiveExpr { Op("<=", r, s) }
	| r=RelationalExpr '>=' s=AdditiveExpr { Op(">=", r, s) }
	| AdditiveExpr

AdditiveExpr: UnionExpr
UnionExpr: PathExpr
PathExpr:
	| FilterExpr
	| LocationPath
FilterExpr: PrimaryExpr

FunctionCall: r=FunctionName '(' s=Arguments? ')' { Func(r, s or []) }
FunctionName: r=NAME { r.string }
Arguments: r=','.Argument+ { r }
Argument: Expr

Literal: r=STRING { r.string }
