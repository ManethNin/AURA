# Guava Release 18.0: Release Notes

## API Changes

[Full JDiff Report](http://google.github.io/guava/releases/18.0/api/diffs/) of changes since release 17.0.

To build a combined report of the API changes between release 18.0 and any older release, check out our docs tree and run `jdiff/jdiff.sh` with the previous release number as argument (example: `jdiff.sh 5.0`).

### Significant API additions and changes

#### common.base

  * `MoreObjects`
    * Methods in `Objects` which do not have equivalents in `java.util.Objects` have been moved to `MoreObjects` to allow importing of both classes. Those methods have been deprecated in our `Objects` class. Methods which _do_ have equivalents in `java.util.Objects` will remain (undeprecated) in our `Objects` class as long as Guava continues to support JDK 6.
  * Enums` - removed deprecated `valueOfFunction` method.

#### common.collect

  * `FluentIterable.of(E[])`
  * `FluentIterable.append(E...)`
  * `FluentIterable.append(Iterable<? extends E>)`
  * `FluentIterable.join(Joiner)`

#### common.hash

  * `Hashing.crc32c()`

`BloomFilter` no longer recognizes the system property `com.google.common.hash.BloomFilter.useMitz32` (see [[Release 17 - A note on BloomFilter|Release17#A-note_on-BloomFilter]] for more information).

#### common.io

Methods which took an `InputSupplier` or `OutputSupplier` parameter or which returned an `InputSupplier` or `OutputSupplier` (all of which were deprecated in Guava 15.0) have been removed. Additionally, `ByteSource`, `ByteSink`, `CharSource` and `CharSink` no longer implement `InputSupplier` or `OutputSupplier`.

The `InputSupplier` and `OutputSupplier` interfaces, which no longer have any usages in Guava, will be deleted in December 2015.

#### common.net

  * `InetAddresses.decrement(InetAddress)`

#### common.reflect

  * `Parameter.getAnnotationsByType(Class<A>)`
  * `Parameter.getDeclaredAnnotation(Class<A>)`
  * `Parameter.getDeclaredAnnotationsByType(Class<A>)`

#### common.util.concurrent

  * `MoreExecutors.directExecutor()` - lightweight, simple `Executor` that runs tasks on the thread that invokes `execute`.
  * `MoreExecutors.newDirectExecutorService()` - heavier `ListeningExecutorService` implementation of the same thing; equivalent to `sameThreadExecutor()`, which has been deprecated.
