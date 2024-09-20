import random

class BracketNode:
    def __init__(self, val=None, left=None, right=None, parent=None):
        self.val = val
        self.left = left
        self.right = right
        self.parent = parent

class Bracket:
    def __init__(self, root_value=None):
        self.root = BracketNode(root_value)

    def insert_left(self, node, value):
        if not node.left:
            node.left = BracketNode(value, parent=node)
            return
        new_node = BracketNode(val=value, left=node.left, parent=node)
        node.left = new_node

    def insert_right(self, node, value):
        if not node.right:
            node.right = BracketNode(value)
            return
        new_node = BracketNode(val=value, right=node.right, parent=node)
        node.right = new_node

    def count_leaves(self):
        return self._count_leaves(self.root)

    def _count_leaves(self, node):
        if not node:
            return 0
        if not node.left and not node.right:
            return 1
        
        return self._count_leaves(node.left) + self._count_leaves(node.right)

    def create_bracket(self, height, leaf_nodes):
        self.root = self._create_bracket(height, leaf_nodes, None)
        return self

    def _create_bracket(self, height, leaf_nodes, parent):
        if height == 0:
            node = BracketNode(val=random.randint(1,100), parent=parent)
            return node
        elif leaf_nodes == 1:
            node = BracketNode(val=random.randint(1,100), parent=parent)
            return node
        else:
            node = BracketNode(val=random.randint(1,100), parent=parent)

            if random.random() < 0.5:
                node.left = self._create_bracket(height - 1, leaf_nodes // 2, node)
                node.right = self._create_bracket(height - 1, leaf_nodes - leaf_nodes // 2, node)
            else:
                node.right = self._create_bracket(height - 1, leaf_nodes // 2, node)
                node.left = self._create_bracket(height -1, leaf_nodes - leaf_nodes // 2, node)
            return node
    
    def show_tree(self):
        return self._show_tree(self.root)

    def _show_tree(self, root, prefix="", is_left=True):
        if not root:
            return "Empty Tree"

        string_representation = ""

        if root.right:
            string_representation += self._show_tree(root.right, prefix + ("│         " if is_left else "          "), False)

        string_representation += prefix + ("└──────── " if is_left else "┌──────── ") + str(root.val) + "\n"

        if root.left:
            string_representation += self._show_tree(root.left, prefix + ("          " if is_left else "│         "), True)

        return string_representation

    def from_dict(self, bracket: dict,):
        self.root = self._from_dict(bracket)
        return self
    
    def _from_dict(self, bracket: dict, parent=None):
        if not bracket:
            return
        
        root = BracketNode(bracket['value'], parent=parent)
        root.left = self._from_dict(bracket.get('left'), parent=root)
        root.right = self._from_dict(bracket.get('right'), parent=root)

        return root

    def _to_dict(self, root):
        if not root:
            return
        
        return {
            "value": root.val,
            "left": self._to_dict(root.left),
            "right": self._to_dict(root.right),
        }

    def __iter__(self):
        yield from self._to_dict(self.root).items()

    def __str__(self):
        def recurse(node, depth):
            if node is None:
                return ""
            result = ""
            result += "  " * depth + str(node.value) + "\n"
            result += recurse(node.left, depth + 1)
            result += recurse(node.right, depth + 1)
            return result
        
        return recurse(self.root, 0)    

    
