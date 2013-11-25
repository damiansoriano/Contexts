import datetime
import sys
from io import StringIO
from . import shared


class DotsReporter(shared.StreamReporter):
    def assertion_passed(self, *args, **kwargs):
        super().assertion_passed(*args, **kwargs)
        self._print('.', end='')

    def assertion_failed(self, *args, **kwargs):
        super().assertion_failed(*args, **kwargs)
        self._print('F', end='')

    def assertion_errored(self, *args, **kwargs):
        super().assertion_errored(*args, **kwargs)
        self._print('E', end='')

    def context_errored(self, *args, **kwargs):
        super().context_errored(*args, **kwargs)
        self._print('E', end='')

    def unexpected_error(self, *args, **kwargs):
        super().unexpected_error(*args, **kwargs)
        self._print('E', end='')


class SummarisingReporter(shared.SimpleReporter, shared.StreamReporter):
    dashes = '-' * 70

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.summary = []
        self.current_summary = None
        self.current_indent = ''

    def context_started(self, context):
        super().context_started(context)
        self.current_summary = [self.suite_view_model.contexts[context].name]
        self.indent()

    def context_ended(self, context):
        super().context_ended(context)
        ctx = self.suite_view_model.contexts[context]
        if ctx.assertion_failures or ctx.assertion_errors:
            self.add_current_context_to_summary()
        self.dedent()
        self.current_summary = None

    def context_errored(self, context, exception):
        super().context_errored(context, exception)
        ctx = self.suite_view_model.contexts[context]
        self.extend_summary(ctx.error_summary)
        self.add_current_context_to_summary()
        self.dedent()
        self.current_summary = None

    def assertion_failed(self, assertion, exception):
        super().assertion_failed(assertion, exception)
        self.add_assertion_to_summary(assertion)

    def assertion_errored(self, assertion, exception):
        super().assertion_errored(assertion, exception)
        self.add_assertion_to_summary(assertion)

    def suite_ended(self, suite):
        super().suite_ended(suite)
        self.summarise()

    def unexpected_error(self, exception):
        super().unexpected_error(exception)
        formatted_exc = self.suite_view_model.unexpected_errors[-1]
        self.extend_summary(formatted_exc)

    def indent(self):
        self.current_indent += '  '

    def dedent(self):
        self.current_indent = self.current_indent[:-2]

    def append_to_summary(self, string):
        if self.current_summary is not None:
            self.current_summary.append(self.current_indent + string)
        else:
            self.summary.append(self.current_indent + string)

    def extend_summary(self, iterable):
        if self.current_summary is not None:
            self.current_summary.extend(self.current_indent + s for s in iterable)
        else:
            self.summary.extend(self.current_indent + s for s in iterable)

    def add_current_context_to_summary(self):
        self.summary.extend(self.current_summary)

    def add_assertion_to_summary(self, assertion):
        assertion_vm = self.suite_view_model.current_context.assertions[assertion]
        formatted_exc = assertion_vm.error_summary

        if assertion_vm.status == "errored":
            self.append_to_summary('ERROR: ' + assertion_vm.name)
        elif assertion_vm.status == "failed":
            self.append_to_summary('FAIL: ' + assertion_vm.name)

        self.indent()
        self.extend_summary(formatted_exc)
        self.dedent()

    def summarise(self):
        self._print('')
        self._print(self.dashes)
        if self.suite_view_model.failed:
            self._print('\n'.join(self.summary))
            self._print(self.dashes)
            self._print('FAILED!')
            self._print(self.failure_numbers())
        else:
            self._print('PASSED!')
            self._print(self.success_numbers())

    def success_numbers(self):
        return "{}, {}".format(
            pluralise("context", len(self.suite_view_model.contexts)),
            pluralise("assertion", len(self.suite_view_model.assertions)))

    def failure_numbers(self):
        return "{}, {}: {} failed, {}".format(
            pluralise("context", len(self.suite_view_model.contexts)),
            pluralise("assertion", len(self.suite_view_model.assertions)),
            len(self.suite_view_model.assertion_failures),
            pluralise("error", len(self.suite_view_model.assertion_errors) + len(self.suite_view_model.context_errors) + len(self.suite_view_model.unexpected_errors)))


class VerboseReporter(shared.SimpleReporter, shared.StreamReporter):
    dashes = '-' * 70

    def context_started(self, context):
        super().context_started(context)
        self._print(self.suite_view_model.contexts[context].name)

    def assertion_passed(self, assertion):
        super().assertion_started(assertion)
        self._print('  PASS: ' + self.suite_view_model.current_context.assertions[assertion].name)

    def assertion_failed(self, assertion, exception):
        super().assertion_failed(assertion, exception)
        vm = self.suite_view_model.current_context.assertions[assertion]
        self._print('  FAIL: ' + vm.name)
        self._print('    ' + '\n    '.join(vm.error_summary))

    def assertion_errored(self, assertion, exception):
        super().assertion_errored(assertion, exception)
        vm = self.suite_view_model.current_context.assertions[assertion]
        self._print('  ERROR: ' + vm.name)
        self._print('    ' + '\n    '.join(vm.error_summary))

    def context_errored(self, context, exception):
        super().context_errored(context, exception)
        self._print('  ' + '\n  '.join(self.suite_view_model.contexts[context].error_summary))

    def unexpected_error(self, exception):
        super().unexpected_error(exception)
        self._print('\n'.join(self.suite_view_model.unexpected_errors[-1]))

    def suite_ended(self, suite):
        super().suite_ended(suite)
        self.summarise()

    def summarise(self):
        self._print(self.dashes)
        if self.suite_view_model.failed:
            self._print('FAILED!')
            self._print(self.failure_numbers())
        else:
            self._print('PASSED!')
            self._print(self.success_numbers())

    def success_numbers(self):
        return "{}, {}".format(
            pluralise("context", len(self.suite_view_model.contexts)),
            pluralise("assertion", len(self.suite_view_model.assertions)))

    def failure_numbers(self):
        return "{}, {}: {} failed, {}".format(
            pluralise("context", len(self.suite_view_model.contexts)),
            pluralise("assertion", len(self.suite_view_model.assertions)),
            len(self.suite_view_model.assertion_failures),
            pluralise("error", len(self.suite_view_model.assertion_errors) + len(self.suite_view_model.context_errors) + len(self.suite_view_model.unexpected_errors)))


class LessVerboseReporter(VerboseReporter):
    def __init__(self, stream=sys.stdout):
        super().__init__(stream)
        self.real_stream = stream
        self.stream = StringIO()
        self.to_output_at_end = StringIO()

    def context_started(self, context):
        self.current_context_failed = False
        super().context_started(context)

    def context_ended(self, context):
        super().context_ended(context)
        if self.current_context_failed:
            self.to_output_at_end.write(self.stream.getvalue())
        self.stream = StringIO()

    def context_errored(self, context, exception):
        super().context_errored(context, exception)
        self.to_output_at_end.write(self.stream.getvalue())
        self.stream = StringIO()

    def assertion_passed(self, assertion):
        orig_stream = self.stream
        self.stream = StringIO()
        super().assertion_passed(assertion)
        self.stream = orig_stream

    def assertion_failed(self, assertion, exception):
        super().assertion_failed(assertion, exception)
        self.current_context_failed = True

    def assertion_errored(self, assertion, exception):
        super().assertion_errored(assertion, exception)
        self.current_context_failed = True

    def unexpected_error(self, exception):
        orig_stream = self.stream
        self.stream = self.to_output_at_end
        super().unexpected_error(exception)
        self.stream = orig_stream

    def suite_ended(self, suite):
        output = self.to_output_at_end.getvalue()
        if output:
            self.real_stream.write('\n' + self.dashes + '\n')
            self.real_stream.write(output[:-1])

        self.stream = self.real_stream
        self._print('')
        super().suite_ended(suite)


class StdOutCapturingReporter(SummarisingReporter):
    def context_started(self, context):
        super().context_started(context)
        self.real_stdout = sys.stdout
        self.buffer = StringIO()
        sys.stdout = self.buffer

    def centred_dashes(self, string):
        num = str(70 - len(self.current_indent))
        return ("{:-^"+num+"}").format(string)

    def context_ended(self, context):
        super().context_ended(context)
        sys.stdout = self.real_stdout

    def context_errored(self, context, exception):
        super().context_errored(context, exception)
        sys.stdout = self.real_stdout
        self.add_buffer_to_summary()

    def assertion_failed(self, assertion, exception):
        super().assertion_failed(assertion, exception)
        self.add_buffer_to_summary()

    def assertion_errored(self, assertion, exception):
        super().assertion_errored(assertion, exception)
        self.add_buffer_to_summary()

    def add_buffer_to_summary(self):
        if self.buffer.getvalue():
            self.indent()
            self.append_to_summary(self.centred_dashes(" >> begin captured stdout << "))
            self.extend_summary(self.buffer.getvalue().strip().split('\n'))
            self.append_to_summary(self.centred_dashes(" >> end captured stdout << "))
            self.dedent()


class TimedReporter(shared.StreamReporter):
    def suite_started(self, suite):
        super().suite_started(suite)
        self.start_time = datetime.datetime.now()

    def suite_ended(self, suite):
        super().suite_ended(suite)
        self.end_time = datetime.datetime.now()
        self.print_time()

    def print_time(self):
        total_secs = (self.end_time - self.start_time).total_seconds()
        rounded = round(total_secs, 1)
        self._print("({} seconds)".format(rounded))


def pluralise(noun, num):
    string = str(num) + ' ' + noun
    if num != 1:
        string += 's'
    return string
