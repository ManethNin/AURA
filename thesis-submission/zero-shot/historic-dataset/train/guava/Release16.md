# Guava Release 16.0: Release Notes

## API Changes

[Full JDiff Report](http://google.github.io/guava/releases/16.0/api/diffs/) of changes since release 15.0

To build a combined report of the API changes between release 16.0 and any older release, check out our docs tree and run `jdiff/jdiff.sh` with the previous release number as argument (example: `jdiff.sh 5.0`).

### Significant API additions

#### common.base

`Ascii.equalsIgnoreCase`

`Ascii.truncate`

`Converter`

`CaseFormat.converterTo(CaseFormat)`

`Enums.stringConverter`

`Utf8`

#### common.collect

`MultimapBuilder`

`Maps.asConverter(BiMap)`

#### common.eventbus

`SubscriberExceptionHandler`

#### common.hash

`HashingInputStream`

`HashingOutputStream`

#### common.io

`ByteSource.read(ByteProcessor)`

`CharSource.readLines(LineProcessor)`

#### common.primitives

`Booleans.countTrue(boolean...)`

`stringConverter()` for `Ints`, `Longs`, `Doubles`, `Floats` and `Shorts`

#### common.reflect

`ClassPath.getAllClasses()`

#### common.util.concurrent

`Runnables.doNothing()`

### Significant API changes

In `common.io`, `InputSupplier` and `OutputSupplier` and all methods that take one or the other as a parameter have been deprecated. `ByteSource`, `CharSource`, `ByteSink` and `CharSink` should be used instead. The methods will be removed in two releases (18.0) and the interfaces are scheduled to be removed after 18 months, in June 2015.
