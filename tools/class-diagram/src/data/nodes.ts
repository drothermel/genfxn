import type { NodeDef } from '../types';

export const NODE_DEFS: NodeDef[] = [
  // Protocol
  {
    id: 'Space', kind: 'protocol', file: 'spaces/space.py', badge: 'Protocol',
    desc: 'Runtime-checkable protocol defining the interface all value spaces must implement. Two required methods: validate_member(**kwargs) and sample(n, rng).',
    fields: [
      { name: 'validate_member', type: '(**kwargs) → None' },
      { name: 'sample', type: '(n, rng) → list[Any]' },
    ],
    width: 220,
  },

  // Abstract base
  {
    id: 'BaseOp', kind: 'abstract', file: 'ops/base_op.py', badge: 'ABC',
    desc: 'Pydantic BaseModel + ABC. Owns an input_space (Space), a renderers dict keyed by Lang, and defines the eval/render contract all ops must implement.',
    fields: [
      { name: 'op_type', type: 'Any' },
      { name: 'input_space', type: 'Space' },
      { name: 'renderers', type: 'dict[Lang, StrRenderFn]' },
      { name: 'eval', type: '(**kwargs) → Any  [abstract]' },
      { name: 'render_python', type: '() → str  [abstract]' },
      { name: 'render', type: '(Lang) → str' },
    ],
    width: 260,
  },

  // Concrete ops — BaseOp subclasses
  {
    id: 'MixtureOp', kind: 'op', file: 'ops/mixture_op.py', badge: 'Op',
    desc: 'Weighted random dispatch over registered ops. Validates all choices exist in the registry at construction. At eval time, samples one op and delegates.',
    fields: [
      { name: 'choices', type: 'tuple[str, ...]' },
      { name: 'weights', type: 'list[float]' },
      { name: 'rng', type: 'random.Random' },
    ],
    width: 230,
  },
  {
    id: 'UpperStrOp', kind: 'op-leaf', file: 'ops/string_ops/upper_str_op.py', badge: 'Op',
    desc: 'Uppercases a string. Uses guarded eval/render templates to handle empty strings.',
    fields: [], width: 160,
  },
  {
    id: 'LowerStrOp', kind: 'op-leaf', file: 'ops/string_ops/lower_str_op.py', badge: 'Op',
    desc: 'Lowercases a string.',
    fields: [], width: 160,
  },
  {
    id: 'CapitalizeStrOp', kind: 'op-leaf', file: 'ops/string_ops/capitalize_str_op.py', badge: 'Op',
    desc: 'Capitalizes the first character.',
    fields: [], width: 180,
  },
  {
    id: 'SwapcaseStrOp', kind: 'op-leaf', file: 'ops/string_ops/swapcase_str_op.py', badge: 'Op',
    desc: 'Swaps case of each character.',
    fields: [], width: 175,
  },
  {
    id: 'TitleStrOp', kind: 'op-leaf', file: 'ops/string_ops/title_str_op.py', badge: 'Op',
    desc: 'Title-cases each word.',
    fields: [], width: 150,
  },
  {
    id: 'CasefoldStrOp', kind: 'op-leaf', file: 'ops/string_ops/casefold_str_op.py', badge: 'Op',
    desc: 'Aggressively lowercases for caseless matching.',
    fields: [], width: 175,
  },
  {
    id: 'ReverseStrOp', kind: 'op-leaf', file: 'ops/string_ops/reverse_str_op.py', badge: 'Op',
    desc: 'Reverses a string.',
    fields: [], width: 170,
  },
  {
    id: 'StripStrOp', kind: 'op-leaf', file: 'ops/string_ops/strip_str_op.py', badge: 'Op',
    desc: 'Strips whitespace from both sides.',
    fields: [], width: 155,
  },
  {
    id: 'LstripStrOp', kind: 'op-leaf', file: 'ops/string_ops/lstrip_str_op.py', badge: 'Op',
    desc: 'Left-strips whitespace.',
    fields: [], width: 155,
  },
  {
    id: 'RstripStrOp', kind: 'op-leaf', file: 'ops/string_ops/rstrip_str_op.py', badge: 'Op',
    desc: 'Right-strips whitespace.',
    fields: [], width: 155,
  },
  {
    id: 'TabStrOp', kind: 'op-leaf', file: 'ops/string_ops/tab_str_op.py', badge: 'Op',
    desc: 'Maps any non-empty string to a tab character.',
    fields: [], width: 155,
  },
  {
    id: 'ExpandtabsStrOp', kind: 'op-leaf', file: 'ops/string_ops/expandtabs_str_op.py', badge: 'Op',
    desc: 'Expands tab chars to spaces (tabsize=8).',
    fields: [], width: 195,
  },

  // CompoundOp base
  {
    id: 'CompoundOp', kind: 'abstract', file: 'ops/compound_op.py', badge: 'ABC',
    desc: 'Base class for ops that parameterize over a family of related transforms. Adds transform, transform_space, and input_var fields to BaseOp.',
    fields: [
      { name: 'transform', type: 'Any' },
      { name: 'transform_space', type: 'CategoricalSpace' },
      { name: 'input_var', type: 'str = "x"' },
    ],
    width: 240,
  },

  // Compound ops
  {
    id: 'SimpleStrCompoundOp', kind: 'op', file: 'ops/simple_str_compound_op.py', badge: 'CompoundOp',
    desc: 'Compound op for 11 parameter-free string transforms. Selects transform at construction via SimpleStrTransformType.',
    fields: [
      { name: 'transform', type: 'SimpleStrTransformType' },
      { name: 'transform_space', type: 'SimpleStrTransformSpace' },
      { name: 'input_space', type: 'StringSpace' },
      { name: 'input_var', type: 'str = "s"' },
    ],
    width: 260,
  },
  {
    id: 'CharStyleCompoundOp', kind: 'op', file: 'ops/char_style_compound_op.py', badge: 'CompoundOp',
    desc: 'Compound op for char-style transforms (upper/lower/tab). Operates on lowercase ASCII letters.',
    fields: [
      { name: 'transform', type: 'CharStyleTransformType' },
      { name: 'transform_space', type: 'CharStyleTransformSpace' },
      { name: 'input_space', type: 'CategoricalSpace' },
      { name: 'input_var', type: 'str = "ch"' },
    ],
    width: 260,
  },

  // Spaces — base / generic
  {
    id: 'CategoricalSpace', kind: 'space', file: 'spaces/categorical_space.py', badge: 'Space',
    desc: 'Finite ordered set of values (str|int|float|bool|None). Type-stable equality prevents bool/int collisions. Rejects NaN and duplicates.',
    fields: [{ name: 'values', type: 'tuple[CategoricalValue, ...]' }],
    width: 220,
  },
  {
    id: 'UniformIntSpace', kind: 'space', file: 'spaces/uniform_int_space.py', badge: 'Space',
    desc: 'Uniform integer distribution over [low, high]. Defaults to [0, 10000] (string length range).',
    fields: [
      { name: 'low', type: 'int' },
      { name: 'high', type: 'int' },
    ],
    width: 200,
  },
  {
    id: 'ConstantSpace', kind: 'space', file: 'spaces/constant_space.py', badge: 'Space',
    desc: 'Singleton space — always validates/samples the same value.',
    fields: [{ name: 'value', type: 'ConstantValue' }],
    width: 200,
  },

  // Spaces — CategoricalSpace subclasses
  {
    id: 'AsciiCharSpace', kind: 'space-leaf', file: 'spaces/ascii_char_space.py', badge: 'Space',
    desc: 'CategoricalSpace restricted to single ASCII characters. Also provides a classmethod validate_space() used by StringSpace and SimpleStringInputSpace to validate char spaces.',
    fields: [{ name: 'values', type: 'tuple[str, ...] (128 ASCII)' }],
    width: 230,
  },
  {
    id: 'CharStyleTransformSpace', kind: 'space-leaf', file: 'spaces/char_style_transform_space.py', badge: 'Space',
    desc: 'CategoricalSpace over the three char-style transforms: "upper", "lower", "tab".',
    fields: [{ name: 'values', type: '("upper","lower","tab")' }],
    width: 240,
  },
  {
    id: 'SimpleStrTransformSpace', kind: 'space-leaf', file: 'spaces/simple_str_transform_space.py', badge: 'Space',
    desc: 'CategoricalSpace over the 11 parameter-free string transform names (lowercase, uppercase, capitalize, ...).',
    fields: [{ name: 'values', type: 'tuple[SimpleStrTransformType, ...]' }],
    width: 260,
  },

  // Composite spaces
  {
    id: 'StringSpace', kind: 'space', file: 'spaces/string_space.py', badge: 'Composite Space',
    desc: 'Composes a length_space (UniformIntSpace) and a char_space (CategoricalSpace validated by AsciiCharSpace) to sample/validate strings. The primary input space for most string ops.',
    fields: [
      { name: 'length_space', type: 'Space (→ UniformIntSpace)' },
      { name: 'char_space', type: 'Space (→ AsciiCharSpace)' },
    ],
    width: 270,
  },
  {
    id: 'SimpleStringInputSpace', kind: 'space', file: 'spaces/simple_string_input_space.py', badge: 'Composite Space',
    desc: 'StringSpace subclass that generates realistic test strings by composing: a core_length_space, core_letter_space (lowercase ASCII), a core_style_mixture (MixtureOp over lower/upper/tab), and a pad_space for whitespace padding.',
    fields: [
      { name: 'core_length_space', type: 'Space (→ UniformIntSpace)' },
      { name: 'core_letter_space', type: 'Space (→ CategoricalSpace)' },
      { name: 'core_style_mixture', type: 'MixtureOp' },
      { name: 'pad_space', type: 'Space (→ CategoricalSpace)' },
    ],
    width: 280,
  },

  // Templates
  {
    id: 'str_templates', kind: 'template', file: 'templates/str_templates.py', badge: 'Helpers',
    desc: 'Five helper functions used by all 12 BaseOp string ops. Handle the empty-string guard pattern: eval_guarded_str_expr, render_guarded_str_method, render_guarded_str_method_with_args, render_guarded_str_expr, render_guarded_str_suffix.',
    fields: [
      { name: 'eval_guarded_str_expr', type: '' },
      { name: 'render_guarded_str_method', type: '' },
      { name: 'render_guarded_str_*', type: '(3 variants)' },
    ],
    width: 230,
  },

  // Registries
  {
    id: 'STRING_OP_REGISTRY', kind: 'registry', file: 'ops/string_ops/registry.py', badge: 'Registry',
    desc: 'Maps 12 string op_type names to their BaseOp subclasses. Provides list_string_op_types(), get_string_op_cls(), and build_string_op() helpers.',
    fields: [],
    width: 215,
  },
  {
    id: 'OP_REGISTRY', kind: 'registry', file: 'ops/registry.py', badge: 'Registry',
    desc: 'Top-level registry merging STRING_OP_REGISTRY + MixtureOp. Provides list_op_types(), get_op_cls(), and build_op() — the main factory used by MixtureOp at runtime.',
    fields: [],
    width: 215,
  },

  // Types
  {
    id: 'types', kind: 'types', file: 'types.py', badge: 'Module',
    desc: 'Shared constants and type aliases. Lang enum (PYTHON), Alphabet enum (ASCII), RenderFn, StrRenderFn, and default config values (min/max string length, tab size, input variable name).',
    fields: [
      { name: 'Lang', type: 'StrEnum ("python")' },
      { name: 'Alphabet', type: 'StrEnum ("ascii")' },
      { name: 'RenderFn', type: 'Callable[[str], str]' },
      { name: 'StrRenderFn', type: 'Callable[[], str]' },
    ],
    width: 230,
  },
];
