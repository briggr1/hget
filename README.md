# hget
faster large file downloader

This module is a CLI to download large files over HTTP, such as iso, .zip, etc.

It opens a seperate process for each chunk, and then concatenates the results when finished.

Builtin command line help and tab completion.
