"""Actual repository SQL against disposable SQLite; no PostgreSQL/RLS claim."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Barrier

import pytest

from hoso_api.auth import AuthenticatedUser
from hoso_api.profile import ProfileFields, ProfileUpdate
from hoso_api.portal.repository import (
    ProfileMissing, ProfileRepository, RevisionConflict, StorageUnavailable,
)
from hoso_api.portal.service import ProfileService


A = AuthenticatedUser(subject="user_synthetic_a", session_id="session_synthetic_a")
B = AuthenticatedUser(subject="user_synthetic_b", session_id="session_synthetic_b")


def update(revision, name):
    return ProfileUpdate(
        expected_revision=revision,
        fields=ProfileFields(full_name=name, address="Synthetic address\nDòng thử nghiệm"),
    )


def test_missing_reads_and_positive_updates_do_not_create_profiles(repository):
    with pytest.raises(ProfileMissing):
        repository.read(A)
    with pytest.raises(ProfileMissing):
        repository.write(A, update(1, "Synthetic A"))
    with pytest.raises(ProfileMissing):
        repository.read(A)


def test_a_and_b_cannot_read_or_overwrite_each_other(repository):
    a = repository.write(A, update(0, "Synthetic Nguyễn A"))
    with pytest.raises(ProfileMissing):
        repository.read(B)
    with pytest.raises(ProfileMissing):
        repository.write(B, update(a.revision, "Synthetic B attack"))
    b = repository.write(B, update(0, "Synthetic Trần B"))
    assert a.profile_id != b.profile_id
    repository.write(A, update(a.revision, "Synthetic A edited"))
    assert repository.read(B) == b
    assert repository.read(A).fields.full_name == "Synthetic A edited"
    repository.write(B, update(b.revision, "Synthetic B edited"))
    assert repository.read(A).revision == 2
    assert repository.read(A).fields.full_name == "Synthetic A edited"


def test_stale_creation_update_and_null_replacement(repository):
    first = repository.write(A, update(0, "Synthetic"))
    with pytest.raises(RevisionConflict):
        repository.write(A, update(0, "Replacement"))
    second = repository.write(A, ProfileUpdate(expected_revision=first.revision, fields={}))
    assert second.profile_id == first.profile_id
    assert second.revision == first.revision + 1
    assert all(value is None for value in second.fields.model_dump().values())
    with pytest.raises(RevisionConflict):
        repository.write(A, update(first.revision, "Stale"))
    assert repository.read(A) == second


@pytest.mark.parametrize("revision", [0, 1])
def test_simultaneous_writes_have_one_winner(repository, revision):
    if revision:
        repository.write(A, update(0, "Original"))
    barrier = Barrier(2)

    def save(name):
        barrier.wait(timeout=10)
        try:
            return repository.write(A, update(revision, name))
        except RevisionConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(save, ["Synthetic first", "Synthetic second"]))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    assert winners[0].revision == revision + 1
    assert repository.read(A) == winners[0]


def test_failed_commit_rolls_back_and_sanitizes_error(transactions, repository):
    class FailingCommit:
        @contextmanager
        def for_user(self, user):
            with transactions.for_user(user) as connection:
                yield connection
                raise RuntimeError("synthetic-private-marker and connection credential")

    broken = ProfileService(ProfileRepository(FailingCommit()))
    with pytest.raises(StorageUnavailable) as failure:
        broken.write(A, update(0, "Synthetic"))
    assert str(failure.value) == ""
    assert failure.value.__suppress_context__ is True
    with pytest.raises(ProfileMissing):
        repository.read(A)


def test_no_raw_client_identity_argument_and_no_mutable_response_alias(repository):
    with pytest.raises(StorageUnavailable):
        repository.read("user_synthetic_a")
    saved = repository.write(A, update(0, "Synthetic saved"))
    saved.fields.full_name = "Local form correction only"
    assert repository.read(A).fields.full_name == "Synthetic saved"


def test_invalid_mutated_payload_is_not_persisted(service, repository):
    payload = update(0, "Synthetic")
    payload.expected_revision = True
    with pytest.raises(StorageUnavailable):
        service.write(A, payload)
    with pytest.raises(ProfileMissing):
        repository.read(A)
