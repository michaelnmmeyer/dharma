<a id="dharma.tree"></a>

# dharma.tree

XML tree representation.

Node types are: `Tree`, `Tag`, `Comment`, `String`, `Instruction`. Attributes
are not represented as nodes, even though they are treated like that in the
xpath model, because this would be weird in python.

All node types derive from an abstract base class `Node`. `Tree` and `Tag` nodes
derive from a `Branch` abstract class, which itself derives from `Node`. There
is no inheritance relationship between concrete node types. For instance,
`Comment` is not a subclass of `String`, unlike in bs4. Thus, to check whether a
node is of a concrete given type `T`, using `isinstance(node, T)`, etc. is
sufficient. And to check whether a node is a branch or a leaf, it is sufficient
to check `isinstance(node, Branch)`.

When parsing documents and when modifying attributes, we always normalize spaces
in attributes: we replace all sequences of whitespace characters with " " and we
trim whitespace from both sides.

For simplicity, we do not deal with XML namespaces at all. We just remove
namespace prefixes in both elements and attributes. Thus,
`<xsl:template>` becomes `<template>`, and `<foo xml:lang="eng">` becomes `<foo
lang="eng">`. This means that we cannot deal with documents where namespaces are
significant. This also means that we cannot properly serialize XML documents
that used namespaces initially.

We use XPath expressions for searching and matching, but only support a small
subset of it. Most notably, it is only possible to
select `Tag` and `Tree` nodes. Other types of nodes, attributes in particular,
can only be used in predicates, as in `foo[@bar]`. We also do not support
expressions that index node sets in some way: testing a node position in a node
set or evaluating the length of a node set is not possible.

XPath expressions can use the following functions:

`glob(pattern[, text])`

Checks if `text` matches the given glob `pattern`. If `text` is not given,
it defaults to the node's text contents.

`regex(pattern[, text])`

Like `glob`, but for regular expressions. Matching is unanchored.

`lang()`, `mixed()`, `empty()`, `errors()`

Returns the corresponding attributes in `Node`.

To evaluate an expression, we first convert it to straightforward python source
code, then compile the result, and finally run the code. Compiled expressions
are saved in a global table and are systematically reused. There is no caching
policy for now.

<a id="dharma.tree.Location"></a>

#### Location

Represents the location of a node in an XML file. Fields are:

* `start`: byte index of the start of the node
* `end`: idem for the end of the node
* `line`: line number (one-based)
* `column`: column number (one-based)

<a id="dharma.tree.parse_string"></a>

#### parse\_string

```python
def parse_string(source, path=None)
```

Parse an XML string into a `Tree`. If `path` is given, it will be
used as filename in error messages, and will be accessible through
the `file` attribute.

<a id="dharma.tree.parse"></a>

#### parse

```python
def parse(file, path=None)
```

Parse an XML file into a `Tree`. The `file` argument can either be a
file-like object or a string that indicates the file's path. The `path`
argument can be used to indicate the file's path, for errors messages.
If it is not given, the path of the file will be deduced from `file`,
if possible.

<a id="dharma.tree.Node"></a>

## Node Objects

```python
class Node()
```

<a id="dharma.tree.Node.tree"></a>

#### tree

```python
@property
def tree()
```

The `Tree` this node belongs to. If the node is a `Tree`,
this returns the `Tree` itself.

<a id="dharma.tree.Node.file"></a>

#### file

```python
@property
def file()
```

Path of the XML file this subtree was constructed from.

<a id="dharma.tree.Node.location"></a>

#### location

`Location` object, which indicates the boundaries of the subtree in the
XML source it was constructed from. If the subtree does not come from an
XML file, `Location` is `None`. Likewise, if the subtree is modified in
some way, or if it is extracted from the original tree or copied from it,
`Location` will be set to `None`.

<a id="dharma.tree.Node.parent"></a>

#### parent

```python
@property
def parent()
```

Parent node. All nodes have a parent, except `Tree` nodes,
whose parent is `None`.

<a id="dharma.tree.Node.path"></a>

#### path

```python
@property
def path()
```

The path of this node. See the `locate` method.

<a id="dharma.tree.Node.mixed"></a>

#### mixed

```python
@property
def mixed()
```

Whether this node has both `Tag` and non-blank `String`
children. This can only be called on `Branch` nodes.

<a id="dharma.tree.Node.empty"></a>

#### empty

```python
@property
def empty()
```

`True` if this node has no `Tag` children nor non-blank
`String` children. This can only be called on `Branch` nodes.

<a id="dharma.tree.Node.source"></a>

#### source

```python
@property
def source()
```

XML source of this subtree, as it appears in the file it
was parsed from, as a string. If the `location` member is
`None`, `source` will also be `None`.

<a id="dharma.tree.Node.byte_source"></a>

#### byte\_source

```python
@property
def byte_source()
```

XML source of this subtree, in bytes, encoded as UTF-8.

<a id="dharma.tree.Node.root"></a>

#### root

```python
@property
def root()
```

The root `Tag` node of the `Tree` this subtree belongs to.

<a id="dharma.tree.Node.stuck_child"></a>

#### stuck\_child

```python
def stuck_child()
```

Returns the first `Tag` child of this node, if it has one
and if there is no intervening non-blank text in-between.

<a id="dharma.tree.Node.delete"></a>

#### delete

```python
def delete()
```

Removes this node and all its descendants from the tree.
Returns the removed subtree.

<a id="dharma.tree.Node.locate"></a>

#### locate

```python
def locate(path)
```

Finds the node that matches the given xpath expression.
This only works for basic expressions of the form:
`/`, `/foo[1]`, `/foo[1]/bar[5]`, etc. The path of a node
is given in its `path` attribute.

<a id="dharma.tree.Node.find"></a>

#### find

```python
def find(path)
```

Finds nodes that match the given XPath expression. Returns a
list of matching nodes.

<a id="dharma.tree.Node.first"></a>

#### first

```python
def first(path)
```

Like the `find` method, but returns only the first matching
node, or `None` if there is no match.

<a id="dharma.tree.Node.match_func"></a>

#### match\_func

```python
@staticmethod
def match_func(path)
```

Returns a function that matches the given path if called on
a `Node` object. See the documentation of `Node.matches()`.

<a id="dharma.tree.Node.matches"></a>

#### matches

```python
def matches(path)
```

Checks if this node matches the given XPath expression.
Returns a boolean.

The expression is evaluated like an XSLT pattern. For details,
see the XSLT 1.0 standard, under § 5.2 Patterns.

<a id="dharma.tree.Node.children"></a>

#### children

```python
def children()
```

Returns a list of `Tag` children of this node.

<a id="dharma.tree.Node.replace_with"></a>

#### replace\_with

```python
def replace_with(other)
```

Removes this node and its descendants from the tree, and
puts another node in its place. Returns the removed subtree.

<a id="dharma.tree.Node.text"></a>

#### text

```python
def text(space="default")
```

Returns the text contents of this subtree. Per default, we do
normalize-space(); to prevent this, pass `space="preserve"`.

<a id="dharma.tree.Node.xml"></a>

#### xml

```python
def xml(pretty=False,
        strip_comments=False,
        strip_instructions=False,
        html=False,
        color=False)
```

Returns an XML representation of this subtree.

If `html` is true, the result will be escaped, for inclusion
in an HTML file. If `color` is true, the result will be
colorized, either through CSS classes (if `html` is true),
or with ANSI escapes codes (otherwise).

<a id="dharma.tree.Node.copy"></a>

#### copy

```python
def copy()
```

Makes a copy of this subtree. The returned object holds no
reference to the original. It is bound to a new `Tree`.

<a id="dharma.tree.Node.unwrap"></a>

#### unwrap

```python
def unwrap()
```

Removes a node from the tree but leaves its descendants
in-place. Returns the detached node.

This cannot be called on a `Tree` node. Also note that
unwrapping the root `Tag` node of a `Tree` might yield
an invalid XML document that contains several roots.

<a id="dharma.tree.Node.coalesce"></a>

#### coalesce

```python
def coalesce()
```

Coalesces adjacent string nodes and removes empty string
nodes from this subtree. Has no effect on leaf nodes. In
particular, if this is  called on an empty `String` node, this
node will not be removed from the tree.

<a id="dharma.tree.Branch"></a>

## Branch Objects

```python
class Branch(Node, list)
```

Base class for non-leaf nodes viz. `Tree` nodes and `Tag` nodes.

Branches are represented as lists of nodes. They support most `list`
operations. Those that are not implemented will raise an exception if
called.

<a id="dharma.tree.Tree"></a>

## Tree Objects

```python
class Tree(Branch)
```

`Tree` represents the XML document proper. It must contain a single
tag node and optionally comments and processing instructions. `Tree`
objects constructed from files also hold blank `String` nodes for
new lines, etc.

<a id="dharma.tree.Tag"></a>

## Tag Objects

```python
class Tag(Branch)
```

Represents element nodes.

`Tag` objects have both a `list`-like and a `dict`-like interface.

When they are indexed with integers, the children of the node are
accessed. When they are indexed with strings, XML attributes are
accessed. Indexing an attribute that the `Tag` does not possess is
not treated as an error, and returns the empty string.

The `in` operator also takes types into account: if a `Node` is given,
it will check whether this node is a child of `Tag`. Otherwise, it
assumes the argument is an attribute name, and checks whether the
`Tag` bears this attribute.

Iterating over a `Tag` node yields the tag's children. The methods
`keys()`, `values()` and `items()` can be used for iterating over
attributes.

<a id="dharma.tree.Tag.__init__"></a>

#### \_\_init\_\_

```python
def __init__(name, *attributes_iter, **attributes)
```

The argument `name` is the name of the node as a string, e.g.
"html". This argument can be followed by a single positional
argument `attributes_iter`. If given, it must be an
iterator that returns tuples of the form `(key, value)`, or a
`dict` subclass. Attributes can also be passed as keyword
arguments with `**attributes`.

Attributes ordering is preserved for attributes passed through
`attributes_iter`. This is the reason we have it. New
attributes created manually with e.g. `node["attr"] = "foo"`
are added at the end of the attributes list. (We use an
OrderedDict under the hood.)

<a id="dharma.tree.String"></a>

## String Objects

```python
class String(Node, collections.UserString)
```

Represents a text node.

`String` nodes behave like normal `str` objects, but they can also be
edited in-place with the following methods.

<a id="dharma.tree.String.clear"></a>

#### clear

```python
def clear()
```

Sets this `String` to the empty string.

<a id="dharma.tree.String.append"></a>

#### append

```python
def append(data)
```

Adds text at the end of this `String`.

<a id="dharma.tree.String.prepend"></a>

#### prepend

```python
def prepend(data)
```

Adds text at the beginning of this `String`.

<a id="dharma.tree.String.insert"></a>

#### insert

```python
def insert(index, data)
```

Adds text at the given index of this `String`.

<a id="dharma.tree.Comment"></a>

## Comment Objects

```python
class Comment(Node, collections.UserString)
```

Represents a comment.

`Comment` nodes behave like strings.

<a id="dharma.tree.Instruction"></a>

## Instruction Objects

```python
class Instruction(Node)
```

Represents a processing instruction.

Initial XML declarations e.g. `<?xml version="1.0"?>` are also
represented as processing instructions.

<a id="dharma.tree.Error"></a>

## Error Objects

```python
class Error(Exception)
```

Raised for parsing errors.

