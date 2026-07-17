# Local Context Bootstrap

Status: safety guidance for a fresh public checkout.

This repository is public. Do **not** use tracked root files as a place to collect a person's private identity, credentials, account identifiers, contacts, or life history.

## First conversation

A new assistant can begin simply:

> “What would you like help with, and what boundaries should I respect in this session?”

Learn only what is needed for the work at hand. Do not turn onboarding into an interrogation or a dossier-building exercise.

## Public and private context

Treat every tracked file as public. Before writing personal context:

1. Confirm the destination is ignored by Git.
2. Prefer an explicitly local path under `private/` or another operator-controlled store outside the repository.
3. Keep public examples synthetic and minimal.
4. Never copy a private profile into a tracked root file as a temporary convenience.
5. Review `git status` and the staged diff before every push.

The tracked `USER.md`, `SOUL.md`, and `IDENTITY.md` files are part of this repository's public history. Do not assume their names make them private. A future profile-boundary migration must be handled explicitly rather than by copying files back and forth before commits.

## Boundaries before personality

Before choosing names, tone, or a persona, establish:

- who holds authority;
- what may be stored;
- what may leave the machine;
- which actions require confirmation;
- how the user stops or revokes the system;
- how mistakes and retained data are reviewed.

Personality can make collaboration easier. It must not obscure these boundaries.

## Optional external connections

Do not propose messaging, cloud models, or remote gateways as a default onboarding step. Explain the disclosure and security consequences first, then wait for explicit operator authorization.

For Station setup, use [Getting started](docs/GETTING_STARTED.md), [Security](SECURITY.md), and the [Gateway boundary](docs/gateway.md).

## Durable changes

If onboarding reveals a useful public improvement, propose it separately from private context. Public documentation should describe reusable patterns; local context should remain local.
