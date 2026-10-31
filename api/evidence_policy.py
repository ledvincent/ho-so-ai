"""A scoped review never upgrades sources to legally current or approves a form."""
VERSION='scoped-evidence-1'
def allowed(ready, review, run_id, profile_id):
    return ready is True or (review.get('policy')==VERSION
        and review.get('access')=='source_attributed'
        and str(review.get('run_id'))==str(run_id)
        and review.get('profile_id')==profile_id)
