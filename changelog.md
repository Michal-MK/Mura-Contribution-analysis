1.1
- Added changelog
- Added `config.blame_unseen` - When the analysis starts from different point in time than the beginning of the repository,
  there are two ways to treat file ownership of already existing files: Use `git-blame` and obtain the ownership that way
  or assign ownership to a fictional entity and track only changes from that point on.
- fix populate_previously_unseen_file to use `config.blame_unseen`
- fix `contrib_equal` using `and` instead of `or` when checking name and email of the contributor
- fixed crashes with naive datetime objects
- beneficiaries are no longer duplicated when handling remote repositories
- add basic filtering of the fictional entity to various outputs WIP

1.0
- Initial release