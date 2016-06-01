"Utilities to create writers."
import csv
import nx_misc


# Do not consider context methods private
class HeaderlessMixin:        # pylint: disable=too-few-public-methods
    "Mixin for writers that do not support headers."
    _wrtr = None
    _closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        "Close the underlying objects."
        if not self._closed:
            self._closed = True
            self._wrtr, wrtr = None, self._wrtr
            wrtr.close()

    def _write(self, lst):
        self._wrtr.write(lst)


class HeaderMixin:
    "Mixin for writers that support headers."
    _wrtr = None
    _fobj = None
    _fields_used = None
    _closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        "Close the underlying objects."
        if not self._closed:
            self._closed = True
            self._wrtr, wrtr = None, self._wrtr
            try:
                if self.minimize:
                    self._fobj, fobj = None, self._fobj
                    try:
                        fobj.seek(0)
                        fields = [x for x in self.fields
                                  if x in self._fields_used]
                        if not fields:
                            fields = self.fields
                        write = wrtr.write
                        write(fields)
                        for data in csv.DictReader(fobj, delimiter='|'):
                            data = nx_misc.flatten_dict(data, fields,
                                                        rest_val=None,
                                                        extras_action='ignore',
                                                        field_set=None)
                            write(data)
                    finally:
                        fobj.close()
            finally:
                wrtr.close()

    def write_header(self):
        "Write the header."
        if self.minimize:
            raise ValueError('unsupported operation')
        self._wrtr.write(self.fields)

    def _write(self, lst):
        handler = self.handler
        if handler:
            data = handler(lst)
            if data is None:
                return
            if len(data) != len(lst):
                raise AttributeError('data length changed in handler', lst,
                                     data)
        else:
            data = lst
        if self.minimize:
            self._fields_used.update({k for k, v in zip(self.fields, data)
                                      if v is not None and str(v).strip()})
            self._csv_wrtr.writerow(data)
        else:
            self._wrtr.write(data)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.minimize:
            self._csv_wrtr = csv.writer(self._fobj, delimiter='|',
                                        lineterminator='\n')
            self._csv_wrtr.writerow(self.fields)


# Mixin needed to abrstract writes
class DictWriterMixin:        # pylint: disable=too-few-public-methods
    "Mixin to provide a write method for dictionary writers."
    def write(self, data):
        "Write the data."
        lst = nx_misc.flatten_dict(data, self.fields, rest_val=self.rest_val,
                                   extras_action=self.extras_action,
                                   field_set=self._field_set)
        self._write(lst)


# Mixin needed to abrstract writes
class ObjWriterMixin:        # pylint: disable=too-few-public-methods
    "Mixin to provide a write method for object writers."
    def write(self, data):
        "Write the data."
        lst = nx_misc.flatten_obj(data, self.fields, rest_val=self.rest_val)
        self._write(lst)
