# Guava Release 12.0: Release Notes


## API Changes

[Full JDiff Report](http://google.github.io/guava/releases/12.0/api/diffs/) of changes since release 11.0.2

To build a combined report of the API changes between release 12.0 and any older release, check out our docs tree and run `jdiff/jdiff.sh` with the previous release number as argument (example: `jdiff.sh 5.0`).

### CacheBuilder Cache stats

CacheBuilder users who use the Cache stats() method must now opt in by calling recordStats() (as of 12.0-rc2).

### JDK6 APIs

Guava 12.0 is the first release to require JDK6. Users requiring JDK5 compatibility may continue to use Guava 11.0.2 -- or contact us about maintaining a backport.

Here are the new APIs introduced along with our JDK6 dependency:

ImmutableSortedSet implements NavigableSet; ImmutableSortedMap implements NavigableMap.

Added forwarding classes for Deque, NavigableMap, NavigableSet.

Added type-inferring factory methods: newArrayDeque, newLinkedBlockingDeque, newCopyOnWriteArrayList, newCopyOnWriteArraySet.

Added Maps.unmodifiableNavigableMap, Sets.unmodifiableNavigableSet.

### Other significant API additions

Introducing common.reflect, especially TypeToken, a better java.lang.Class.

Introducing MediaType (which may be split into MediaType+MediaRange someday).

Introducing FluentIterable.

Introducing CacheBuilderSpec; see CacheBuilder.from(CacheBuilderSpec) and CacheBuilder.from(String) to make use of it.

Introducing ImmutableSortedMultiset.

Added Enums.getField, getIfPresent.

Added HashCodes.

Added BloomFilter.copy, equals, hashCode; plus, put now returns boolean.

Added Optional.transform.

Added ToStringHelper.omitNullValues.

Added Collections2.permutations, orderedPermutations.

Added FowardingSet.standardRemoveAll.

Added Cache.putAll.

Added JdkFutureAdapters.listenInPoolThread with custom executor.

### Other significant API changes

Sink is renamed to PrimitiveSink. Implementations of Funnel will need to be updated.

AbstractLinkedIterator has been deprecated in favor of the identical AbstractSequentialIterator.

ByteStreams and Files getDigest methods have been deprecated in favor of new hash methods.

ComparisonChain.compare(boolean, boolean) has been deprecated in favor new compareFalseFirst/compareTrueFirst methods.

### OSGi support

As of 12.0-rc2, Guava contains OSGi metadata.
