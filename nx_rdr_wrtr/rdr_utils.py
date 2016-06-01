"Utilities to create readers."


# Class is abstract
class BaseLine:     # pylint: disable=no-member,too-few-public-methods
    "Base line object to include line number in repr call."
    def __repr__(self):
        return 'Line: {} {}'.format(self.line_num, super().__repr__())


# Class is abstract
class MutableLine(BaseLine):  # pylint: disable=too-few-public-methods
    "Line object for a line with an underlying mutable class."
    def __init__(self, data, idx):
        super().__init__(data)
        self.line_num = idx


# Class is abstract
class ImmutableLine(BaseLine):    # pylint: disable=too-few-public-methods
    "Line object for a line with an underlying immutable class."
    def __new__(cls, data, idx):
        obj = super().__new__(cls, data)
        obj.line_num = idx
        return obj


def list_reader(rdr, *, leading_ws=True, trailing_ws=True, ignore_blanks=True,
                ignore=None, handler=None):
    """
    Attach the common wrappers to the base list generator <rdr> to produce a
    list reader generator.
    """
    def lstrip(lst):
        """Left-strip every element of the list, in-place."""
        for idx, elem in enumerate(lst):
            lst[idx] = elem.lstrip()
        return lst

    def rstrip(lst):
        """Right-strip every element of the list, in-place."""
        for idx, elem in enumerate(lst):
            lst[idx] = elem.rstrip()
        return lst

    def strip(lst):
        """Strip every element of the list, in-place."""
        for idx, elem in enumerate(lst):
            lst[idx] = elem.strip()
        return lst

    if not leading_ws and not trailing_ws:
        # wrap the reader to left/right-strip each element in each list
        rdr = map(strip, rdr)           # pylint: disable=bad-builtin
    elif not trailing_ws:
        # wrap the reader to right-strip each element in each list
        rdr = map(rstrip, rdr)          # pylint: disable=bad-builtin
    elif not leading_ws:
        # wrap the reader to left-strip each element in each list
        rdr = map(lstrip, rdr)          # pylint: disable=bad-builtin

    if ignore_blanks:
        # wrap the reader to skip lists that are empty or all blank
        rdr = filter(any, rdr) # pylint: disable=bad-builtin,redefined-variable-type

    if ignore is not None:
        # wrap the reader to skip lists that are equal to <ignore>
        rdr = (x for x in rdr if x != ignore)

    if handler:
        # wrap the reader to process each list through the handler, skipping
        # those that the handler rejects - signified by the handler returning
        # None
        rdr = (x for x in map(handler, rdr) if x is not None) # pylint: disable=bad-builtin

    return rdr


# internal function
# pylint: disable=too-many-arguments
def _get_fields(rdr, fields, handler, leading_ws, trailing_ws, ignore_blanks,
                ignore_rows_with_fields, field_rename):
    """
    Process the map reader arguments, wrapping the reader as needed, and
    return the reader and the fields.
    """
    if fields is not None and field_rename is not None:
        raise ValueError('rename specified with supplied fields')
    if fields is None:
        tmp_rdr = list_reader(rdr, leading_ws=leading_ws,
                              trailing_ws=trailing_ws,
                              ignore_blanks=ignore_blanks, handler=handler)
        fields = next(tmp_rdr)
    else:
        fields = [getattr(col, 'name', col) for col in fields]
    if not fields:
        raise ValueError('no fields specified')
    if field_rename:
        fields = [field_rename.get(x, x) for x in fields]
    if len(fields) != len(set(fields)):
        raise ValueError('duplicate field names', fields)
    ignore = fields if ignore_rows_with_fields else None
    rdr = list_reader(rdr, leading_ws=leading_ws, trailing_ws=trailing_ws,
                      ignore_blanks=ignore_blanks, ignore=ignore,
                      handler=handler)
    return rdr, fields


def _map_reader_gen(rdr, fields, rest_key, rest_val):
    "Generator for a map reader."
    fields_length = len(fields)
    for line in rdr:
        line_length = len(line)
        if line_length == fields_length:
            active_fields = fields
        elif line_length > fields_length:
            if rest_key is None:
                raise ValueError('too many fields', line.line_num,
                                 fields_length, line_length)
            active_fields = fields + \
                            [rest_key + str(x)
                             for x in range(line_length - fields_length)]
            if len(active_fields) != len(set(active_fields)):
                raise ValueError('rest_key generated duplicate key',
                                 line.line_num, active_fields)
        elif rest_val is not None:
            active_fields = fields
            line += [rest_val] * (fields_length - line_length)
        else:
            raise ValueError('insufficient fields', line.line_num,
                             fields_length, line_length)
        yield active_fields, line


def dict_reader(rdr, *, fields=None, handler=None, leading_ws=True,
                trailing_ws=False, ignore_blanks=True, rest_key=None,
                rest_val=None, ignore_rows_with_fields=True,
                field_rename=None):
    "Return a generator that processes a list reader and returns a dictionary."
    rdr, fields = _get_fields(rdr, fields, handler, leading_ws, trailing_ws,
                              ignore_blanks, ignore_rows_with_fields,
                              field_rename)
    if not all(fields):
        raise ValueError('blank field name', fields)
    def _(rdr, fields):
        class Line(MutableLine, dict):
            "Dictionary line."
            pass
        for fields, line in _map_reader_gen(rdr, fields, rest_key, rest_val):
            result = Line({k: v for k, v in zip(fields, line)}, line.line_num)
            yield result
    return _(rdr, fields)


def obj_reader(rdr, ctor, *, fields=None, handler=None, leading_ws=True,
               trailing_ws=False, ignore_blanks=True, rest_key=None,
               rest_val=None, ignore_rows_with_fields=True, field_rename=None):
    "Return a generator that process a list reader and returns an object."
    rdr, fields = _get_fields(rdr, fields, handler, leading_ws, trailing_ws,
                              ignore_blanks, ignore_rows_with_fields,
                              field_rename)
    for field in fields:
        if not field or not field.isidentifier() or field == 'line_num':
            raise ValueError('invalid field name', field)
    def _(rdr, ctor, fields):
        for fields, line in _map_reader_gen(rdr, fields, rest_key, rest_val):
            result = ctor()
            for key, val in zip(fields, line):
                setattr(result, key, val)
            result.line_num = line.line_num
            yield result
    return _(rdr, ctor, fields)
