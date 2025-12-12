# Guava Release 22.0: Release Notes

## API Changes

- Java 8: [Full JDiff Report](http://google.github.io/guava/releases/22.0/api/diffs/) of changes since release 21.0.
- Android: [Full JDiff Report](http://google.github.io/guava/releases/22.0-android/api/diffs/) of changes since release 20.0 (the previous release that could be used on Android).

## Significant API additions and changes

(For Android, see the changes for [[21.0|Release21]], ignoring those that are Java 8 specific, or the JDiff report linked above.)

### common.primitives

New immutable primitive array types! Think of these as `ImmutableList` for primitive types (but not implementing `List` directly).

- `ImmutableIntArray` and `.Builder`
- `ImmutableLongArray` and `.Builder`
- `ImmutableDoubleArray` and `.Builder`

### common.base

- `Stopwatch.elapsed()`: returns the elapsed time as a `java.time.Duration` .
- `Throwables.getCauseAs(Throwable, Class<X>)`: a way of getting the cause of an exception and casting it to a specific type without losing the original exception stack trace if the cause is _not_ that type.

### common.collect

- `Comparators.empties(First|Last)()`: `Comparator`s for `java.util.Optional`s
- `Comparators.(least|greatest)(k, Comparator)`: `Collector`s for collecting the least/greatest `k` elements (according to a `Comparator`) from a `Stream` to a `List` (faster and more memory efficient than sorting and limiting the stream).
- New `Collector`s for `Multiset`s and `Immutable(Sorted)Multiset`s that take a `ToIntFunction` to get counts for elements.
- `RangeMap.putCoalescing(Range<K>, V)`: Inserts the given range and value to the map, merging it with any connected entries with equal values.
- `Streams.forEachPair(Stream, Stream, BiConsumer)`: For-each over pairs of corresponding elements from two streams.
- `Tables.synchronizedTable(Table)`

### common.graph

- All `common.graph` methods that previously accepted `Object` for nodes/edges now require the specified node/edge type. This breaks all custom implementations of `Graph`, `Network` and `ValueGraph`.
- `ValueGraph` no longer extends `Graph`; `Graphs.equivalence()` has been deprecated in favor of the more usual `equals()` methods on each interface (now that `ValueGraph` and `Graph` no longer need to have compatible definitions).

### common.hash

- `BloomFilter.approximateElementCount()`: Estimate of the number of distinct elements that have been added to the Bloom filter.
- `Hashing.md5()` and `Hashing.sha1()`: Deprecated. Will continue to exist to allow interoperation with systems requiring them.

### common.io

- `CharSink.writeLines(Stream[, String])`: Methods for writing elements of a `Stream` of `CharSequence`s as lines to a `CharSink`.
- `CharSource.lines()`: Returns a `Stream<String>` (which must be closed!) of lines of text from a `CharSource`.
- `CharSource.forEachLine(Consumer)`: For-each over the lines of text in a `CharSource`.
- `Files`: Many methods that are redundant with creating a source or sink for a file and calling a method on it are now deprecated.
- `MoreFiles.equal(Path, Path)`: Returns whether or not two files are regular files containing the same bytes.

### common.util.concurrent

- `CheckedFuture`: Deprecated. (See the [javadoc](http://google.github.io/guava/releases/22.0-rc1/api/docs/com/google/common/util/concurrent/CheckedFuture.html) for details.)
- `TimeLimiter`: `callWithTimeout` (taking a `boolean interruptible`) deprecated; `callWithTimeout`, `callUninterruptiblyWithTimeout`, `runWithTimeout` and `runUninterruptiblyWithTimeout` added.

## Additional changes

Guava's dependencies on some annotation-only libraries are no longer `<optional>true</optional>`. This makes them available at runtime and at compile time for libraries that compile against Guava. This fixes some projects' compile errors ([#2721](https://github.com/google/guava/issues/2721)), but it may introduce dependency conflicts into other projects ([#2824](https://github.com/google/guava/issues/2824)). If you see dependency conflicts, we believe you should be safe excluding all but the newest version of each of the annotation libraries.
