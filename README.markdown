mp4-quicktime
=============

A library to allow programmatic access to and manipulation of [MPEG 4
container][MPEG4p14] files.

Philosophy
----------

William Herrera’s (superb) [Audio::M4P::Quicktime Perl module][M4P.pm] does
everything I wanted but is designed for use with small MP4 files, such as AAC
audio downloaded from the iTunes Store. Some of the design decisions, then,
are not apt to working with larger MP4 files such as high-definition video.

This is where my interest lies: I intend for my library to allow access to—and
manipulation of—any size of MP4 file, from half-megabyte AAC audio files
through to multi-gigabyte high-definition multimedia files. Further, it
shouldn’t be constrained, as far as possible, by hardware limitations:
Audio::M4P::Quicktime module is limited by the fact that it loads the entire
MP4 file into memory; for a multi-gigabyte file, this is simply not feasible.

Use cases
---------

- Read the content of an MP4 file
- Create an MP4 file from scratch
- Add atoms (and atom data) to an MP4 file (new or already extant)
- Extract atoms from one MP4 file and add them to another (eg. extract all audio tracks from file A and add them to file B)

Reference
---------

- [ISO 14496-1 Media Format layout](http://xhelmboyx.tripod.com/formats/mp4-layout.txt)


Future plans
------------

- Plugin-style architecture to support other media formats?

[MPEG4p14]: http://en.wikipedia.org/wiki/MPEG-4_Part_14
[M4P.pm]:   http://search.cpan.org/~billh/Audio-M4P-0.51/lib/Audio/M4P/QuickTime.pm
