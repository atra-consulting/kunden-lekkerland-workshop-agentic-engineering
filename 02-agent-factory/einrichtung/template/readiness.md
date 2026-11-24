# Ticket Readiness Criteria

The factory reads this file before every spec run. A separate Copilot call checks the ticket against the criteria
below, reads the code, and writes a verdict. If any criterion applies, the ticket is **not ready**: the factory
writes no spec, comments the reasons and questions on the ticket, and moves it to "Klärung nötig".

To change what counts as "not ready", edit this file. Each criterion is a level-3 heading with its ID in backticks,
then its text. The IDs are the only reason IDs the verdict may use. Add a criterion by adding a section; remove one
by deleting its section. Then rebuild the image (see README.md, "Changing the Factory").

## How to Judge

- A ticket is ready when a developer who knows this repository could write an implementation plan from it without
  asking anyone. Judge the ticket as written, not as you guess it was meant.
- Read the code before you judge. Look up the pages, routes, templates, entities, and tests the ticket touches.
- Small gaps a developer would fill the obvious way are fine. Don't reject a ticket for style, spelling, or a
  missing story format.
- When in doubt between ready and not ready, decide ready only if a wrong guess would be cheap to fix in review.

## Criteria

### `missing_detail`

The goal, the affected page or behavior, or the expected result is unclear. The agent would have to guess.

Example: "Improve the search." Which search, and what should be better?

### `untestable`

At least one acceptance criterion can't fail in an automated test. "Looks nice", "is fast", and "is user-friendly"
can't fail. "Shows at most 10 results" can.

Example: "The tag list should look more modern."

### `already_exists`

The code already does what the ticket asks. Name the file, and the test if there is one.

Example: "Show the number of posts in the heading of the post list", when the template already shows it.

### `contradicts_code`

The ticket contradicts existing behavior or existing tests, and doesn't say that this change is intended. Name the
file or test it contradicts.

Example: "The add-user command accepts the username 'JaneDoe'", when the validator and its test allow only
lowercase usernames and the ticket doesn't say to change that rule.

### `protected_paths`

The ticket needs changes the factory refuses: new packages or dependencies, configuration, CI, build or test
configuration, or the other protected paths listed in the prompt.

Example: "Use the Carbon library for relative dates", which needs a new Composer package.

### `too_big`

The ticket doesn't fit one pull request of about one hour of human work. It needs several independent features,
a data migration plus a new feature, or changes across many unrelated parts of the application.

Example: "Add user profiles with avatars, a follower system, and email notifications."
