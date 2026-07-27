# The external witness handshake

Round QΣ-R⁴ built an evidence membrane and then reported, on every envelope it
wrote, that `producer == verifier`. This document is how that closes.

## What counts

| mode | what the verifier did | independent? |
|---|---|---|
| `attested` | read the envelope and agreed | **no** — a signature, not a computation |
| `recomputed` | ran the command, reported its own digests | **yes**, if the digests match |
| `contradicted` | ran it and got something else | no — and the envelope **fails** |
| `declined` | could not or would not | no |

A distinct party is necessary and not sufficient. If the producer's number is
wrong, an attestation is wrong in exactly the same way. Only a second
*computation* can disagree, which is why `contradicted` is a first-class outcome
rather than an error to retry away — and why, when it happens, the two results
are not averaged and the newer one does not win.

## Running it

The token is a workspace **admin** access token. It is read from the environment
and never written to an envelope, a log, or a file in this repository.

```bash
export GODELIAN_AGENT_TOKEN='...'          # this shell only
python -m aionq.witness artifacts/r4/instrument_benchmark.envelope.json
```

Do not put it in `.env`, in `settings.json`, or on a command line your shell
history keeps. An envelope is a committed artifact; a bearer token inside one
would be a credential leak wearing the costume of provenance.

For CI, add it as a repository secret and expose it to the witness step only.
The step is optional by design: a fork without the secret must still get a green
correctness run, and a missing witness must degrade to "not independently
witnessed" rather than to a failure that hides behind a red build.

## The protocol

The challenge carries the **command** and the **expected digests** — never the
artifact body. A verifier handed the answer can only agree. Digest comparison
happens on the producer side against digests already recorded, so the verifier
reports and does not adjudicate. An unparseable reply is `declined`, never
guessed: a verifier whose answer cannot be read has verified nothing.

## Current status

Reachability is confirmed: the endpoint answers **HTTP 401** through this
container's proxy without a token. That is all that has been established.

**No handshake has run.** No token is present in this environment, so zero
envelopes are externally witnessed and every one still reports
`producer == verifier`. `BRIDGE-R4-GODELIAN_1` is tagged **A**, and its
surrogate says exactly this: the protocol is exercised end to end against a fake
transport in nine tests, and the transport is the one component that needs a
credential and therefore the one component still untested.

Whether Gödelian-1 will actually recompute rather than attest is an empirical
question about that agent, not a property this code can guarantee.
