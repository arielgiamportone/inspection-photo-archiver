# The deploy wipes the install — design for it

**Symptom.** After every release, one watcher would not start on its own, and the alert recipients
set in the UI "were not saved between sessions".

**Cause.** The release procedure on the production machine is: empty the install folder, unzip the new
package on top. Anything saved from the UI into a settings file is gone on the next release, replaced
by whatever the build machine had. The auto-start required a path that only existed in that saved
file, so after a deploy it found nothing and silently did not start.

**What did not work.** Excluding the settings file from the package changes nothing: the production
copy is deleted by the wipe anyway.

**Fix.** Treat the wipe as the contract, not as a bug. **Whatever production needs to start on its own
lives in code or in a versioned config file.** User-saved values still override the defaults; the
defaults just make sure there is always something to fall back on. The UI also got an explicit save
button where a field had only saved on losing focus.

**Rule of thumb.** For each setting ask: "if the install folder were deleted right now, would the
system still start correctly?" If not, the default belongs in the repository.
