# Guava Release 14.0: Release Notes

## API Changes

[Full JDiff Report](http://google.github.io/guava/releases/14.0.1/api/diffs/) of changes since release 13.0.1

To build a combined report of the API changes between release 14.0.1 and any older release, check out our docs tree and run `jdiff/jdiff.sh` with the previous release number as argument (example: `jdiff.sh 5.0`).

### Significant API additions

#### common.collect
ForwardingBlockingDeque

RangeMap, ImmutableRangeMap, TreeRangeMap

RangeSet, ImmutableRangeSet, TreeRangeSet

#### common.io
BaseEncoding

ByteSink & ByteSource

CharSink & CharSource

FileWriteMode

#### common.reflect
ClassPath & ClassInfo

Invokable

Parameter

#### common.util.concurrent
AbstractListeningExecutorService

FutureFallback

ServiceManager & !Listener

### Significant API changes

The static methods in Equivalences have been moved into Equivalence.

The static methods in DiscreteDomains have been moved into DiscreteDomain.

Stopwatch#elapsedMillis and #elapsedTime have been deprecated in favor of #elapsed

`Sets.cartesianProduct` now guarantees iteration in lexicographical order, instead of leaving order unspecified.

### Promoted from `@Beta`

#### common.base
Ticker

ToStringHelper#omitNullValues

Optional#or #transform

#### common.collect
BoundType

Range

FluentIterable

ForwardingDeque, ForwardingNavigableMap, ForwardingNavigableSet

SortedMapDifference

Ordering.{lea,greate}stOf(Itera{ble,tor})

Ordering.max/min(Iterator)

Immutable{Set,List,}Multimap.inverse()

ImmutableMultimap.Builder.order{Value,Key}sBy

Sets.synchronizedNavigableSet

Maps.filter{Values,Keys,Entries}

Maps.synchronizedNavigableMap

Maps.transform{Values,Keys,Entries}

#### common.math

IntMath & LongMath

#### common.net

HttpHeaders

#### common.primitives

Unsigned{Long,Int}s

#### common.util.concurrent

FutureCallback

Futures (many methods)

AsyncFunction

Atomics

AtomicDouble

AtomicDoubleArray & AtomicLongMap

ExecutionError & UncheckedExecutionException

### Non-API changes

RateLimiter getRate/setRate are no longer synchronized on the current instance

`Sets.cartesianProduct`

#### Optimizations

`LongMath.binomial` is significantly faster.

`LongMath.sqrt` is significantly faster.

`ImmutableBiMap` takes ~35% less memory.

`HashBiMap` takes ~40% less memory.

`Ordering.{lea,greate}stOf(elements, k)` still run in /O(n)/ time, but they perform only one pass and use only /O(k)/ extra memory.  (Accordingly, they now have `Iterator` overloads.)

`ImmutableSet` now uses an improved murmur-based rehashing function to improve dispersion.
