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
AxisSpecifier: r=AxisName ':' ':' { r }
AxisName:
	# Python's tokenizer treats these as separate tokens. We should modify
	# it instead of doing the following.
	| "ancestor" "-" "or" "-" "self" { "ancestor-or-self" }
	| "ancestor" { r.string }
	| "child" { r.string }
	| "descendant" "-" "or" "-" "self" { "descendant-or-self" }
	| "descendant" { r.string }
	| "parent" { r.string }
	| "self" { r.string }

NodeTest: NameTest

NameTest:
	| '*' { Step() }
	| r=NAME { assign(Step(), name_test=r.string) }

Predicate: '[' r=PredicateExpr ']' { r }
PredicateExpr:
	| Expr

Expr: OrExpr
PrimaryExpr:
	| '(' r=Expr ')' { r }
	| Literal
	| FunctionCall
	| '@' r=NAME { "(node[%r])" % r.string }

OrExpr:
	| r=OrExpr "or" s=AndExpr { Op("or", r, s) }
	| AndExpr
AndExpr:
	| r=AndExpr "and" s=EqualityExpr { Op("and", r, s) }
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
Arguments:
	| r=Arguments ',' s=Argument { r + [s] }
	| r=Argument { [r] }
Argument: Expr

Literal: r=STRING { r.string }
