# Sprint 21 — Team B Player Stats and Name Consistency

Status: Ready for Engineer

## Summary

Split the old `Leaderboards` surface into a dedicated `Player Stats` workspace, preserve its existing modes, and clean up visible player-name shortening so analysts see full names consistently across the platform.

## Scope

- Add `/player-stats` as the user-facing replacement for `Leaderboards`
- Move the current leaderboard experience there without the custom metric builder
- Redirect `/leaderboards` to `/player-stats`
- Update top navigation and home-page workspace cards to the new route structure
- Update route references that still point to `/leaderboards`
- Fix the compare-page last-name-only display
- Audit high-traffic visible UI surfaces for player-name shortening and use full names instead

## UX Requirements

- Existing leaderboard modes still work:
  - player stats
  - on/off impact
  - top lineups
  - career leaders
- Old links should not break; redirect cleanly
- Compact layouts may truncate visually with CSS but should not replace a full name with a last name
- The page remains readable on mobile

## Implementation Notes

- Reuse the existing leaderboard data hooks and controls
- Keep this sprint frontend-only unless a true blocker is discovered
- Update links on nearby surfaces so the new route names feel intentional, not transitional
- Preserve Hardwood Editorial styling where practical, but do not expand scope into a broader visual redesign

## Verification Targets

- `/player-stats` renders the former leaderboard functionality
- `/leaderboards` redirects to `/player-stats`
- Home and nav link to the new routes
- Compare and other audited surfaces show full player names
