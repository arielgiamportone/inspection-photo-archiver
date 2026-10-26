# One object, five projects: the e-mail with the wrong subject

**Symptom.** A notification for project A went out with project B's name in the subject, while the
body correctly said project A. The files on disk were all correct.

**Cause.** Saving the notification settings for several projects built **one** settings object and
assigned it to all of them, mutating the subject prefix inside the loop:

```python
notif = NotificationSettings(...)            # ONE instance
for project in selected:
    notif.subject_prefix = f"[{project.name}]"
    project.notifications = notif            # all projects share it
    save(project)                            # each file is serialised correctly here
```

Each file was written inside the loop, so disk looked right. But the in-memory cache — which is where
e-mails are built from — had every project pointing at the same object, carrying the last prefix.
The recipient list had the same bug one level down: passing the same list meant editing one
project's recipients edited all of them.

**Fix.** One instance per project, with its **own copy** of every mutable field.

**How it stays fixed.** A test saves for all projects and then checks, **in memory and on disk**, that
each keeps its own prefix and that no two share an object (`is not`). A later copy-paste bug (a new
project created from an old one, prefix left unchanged) led to a second test: invariants checked over
**every profile at rest**, not just the save path.
