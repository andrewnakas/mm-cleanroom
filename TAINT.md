# Taint scan evidence

Verbatim output of the last taint scan saved in the local work directory, committed as evidence.
It was not re-run for this commit; check the log date against the date of the published build.

Command: `python -m games.mm.taint_report dirty/mm.o2r clean/mm.o2r clean/2ship.o2r`

Live-build check (2026-10-19): the published `mm.o2r` and `2ship.o2r` (git blobs bcdddc7006, 5e1ab35d05) equal `D:/n64work/mm/clean/`; this log was written five minutes after mm.o2r. (File name in the work dir: taint19.txt.)

## `taint19.txt` (written 2026-09-26 20:19)

```
taint: 28739 generated streams scanned; 1885 with short coincidental matches; 0 failing (run >= 32 B)
```
