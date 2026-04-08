abs_dir := $(shell pwd)
DOCKER_IMAGE ?= qverify
# Extra args for qverify-v1-pdfs in Docker, e.g. SIM_FLAGS='--num-qubits 64 --shots 40'
SIM_FLAGS ?=
clean_spthy=./tools/clean_spthy
tamarin=./tools/tamarin-prover
TAMARIN_FLAGS= 
# TAMARIN_FLAGS= -c=100
# TAMARIN_FLAGS=+RTS -N16 -RTS # limit number of CPUs used
# TAMARIN_FLAGS=+RTS -s -M1000000000 -RTS # limit amount of memory used

type=EB
Adv=Network
exec=false
auth=false
secrecy=false
ER=FEC
BO=PostM
M4_FLAGS= --define=type=$(type) --define=Adv=$(Adv) --define=auth=$(auth) --define=secrecy=$(secrecy) --define=exec=$(exec) --define=ER=$(ER) --define=BO=$(BO)

# ifeq ($(Adv), Network)
# 	M4_FLAGS=net
# endif

#  make type=EB auth=true ER=REC BO=PostM Adv=Network prove
#  make type=PM auth=true ER=REC BO=SeqA Adv=MaliciousUser  prove

preprocess:
	m4 ${M4_FLAGS} main.m4 > generated_$(type).spthy
	$(clean_spthy) generated_$(type).spthy

test: preprocess
	${tamarin} ${TAMARIN_FLAGS} --quit-on-warning generated_$(type).spthy

prove: preprocess
	${tamarin} ${TAMARIN_FLAGS} --prove --output=generated_$(type).proof generated_$(type).spthy
# --with-dot=$(abs_dir)/tools/tamarin-cleandot.py
# --with-dot=$(abs_dir)/tools/tamarin-cleandot.py


web: preprocess
	${tamarin} interactive generated_$(type).spthy


# Tamarin pipeline without HTML collect (used by Docker; collect runs on host — see docker-gen-proofs).
gen_proofs_nocollect:
	chmod a+x ./tools/compile_models ./tools/gen_proofs ./tools/collect ./tools/clean_spthy ./tools/test_models ./tools/check_incompleted ./tools/setup.sh ./tools/maude/*
	./tools/compile_models
	# ./tools/test_models
	time ./tools/gen_proofs | tee run.log

gen_proofs: gen_proofs_nocollect
	./tools/collect --output=./_output/generated_results.html ./_output/

web_proofs: 
	echo $(abs_dir)
	${tamarin} interactive ./_output/


all: prove web





clean:
	$(RM) -f generated_*
	$(RM) -f client_session_key.aes

clean_tmp:
	$(RM) -f ./_output/*.tmp

clean_theory:
	$(RM) -f ./_output/*.spthy
	

clean_proofs:
	$(RM) -f ./_output/*.proof

clean_all: clean clean_theory clean_proofs clean_tmp
	$(RM) -f run.log



# ─── Docker targets ──────────────────────────────────────────────────────────
# Ensure host _output is writable and (on macOS) strip xattrs that cause EPERM on bind mounts.
.PHONY: docker-prepare-output docker-prepare-host-output
docker-prepare-output:
	mkdir -p ./_output
	chmod -R u+rwX ./_output
	@command -v xattr >/dev/null 2>&1 && xattr -cr ./_output 2>/dev/null || true

# Remove generated theories on the *host* before Tamarin Docker runs. Docker Desktop on macOS
# cannot chmod/unlink/overwrite existing files under ~/Desktop bind mounts (EPERM); creating
# new files after host-side rm works. Does not touch _output/simulation/ or .proof files.
docker-prepare-host-output: docker-prepare-output
	rm -f ./_output/*.spthy ./_output/*.tmp ./_output/.spthy_manifest 2>/dev/null || true

# Build the Docker image (re-run whenever the Dockerfile changes)
docker-build:
	docker compose build

# Full artifact in one command: rebuild image, compile all theories, prove every model (sequential;
# may take many hours), regenerate HTML, then statistical simulation PDFs. Fails if the proof batch
# stops early unless you export GEN_PROOFS_ALLOW_PARTIAL=1 for the Tamarin container.
.PHONY: docker-all
docker-all: docker-build docker-prepare-host-output
	docker compose run --rm tamarin make gen_proofs_nocollect
	python3 ./tools/collect --output=./_output/generated_results.html ./_output/
	docker compose run --rm simulation qverify-v1-pdfs --output-dir /workspace/_output/simulation $(SIM_FLAGS)

# Run the full proof-generation pipeline inside Docker.
# Outputs land in ./_output/ on the HOST (mounted into the container).
# If the container says there is no rule for gen_proofs_nocollect (or other Makefile targets),
# the image predates your Makefile: run `make docker-build` once, then retry.
# Proof batch must finish all theories or gen_proofs exits 1; for an interrupted run + collect anyway,
# export GEN_PROOFS_ALLOW_PARTIAL=1 before invoking make (see docker-compose.yml environment).
docker-gen-proofs: docker-prepare-host-output
	docker compose run --rm tamarin make gen_proofs_nocollect
	python3 ./tools/collect --output=./_output/generated_results.html ./_output/

# Run statistical simulations only; PDFs and CSV land in ./_output/simulation/
docker-simulation: docker-prepare-output
	docker compose run --rm simulation qverify-v1-pdfs --output-dir /workspace/_output/simulation $(SIM_FLAGS)

# Same as docker-all (kept for existing scripts).
docker-gen-proofs-and-simulation: docker-all

# Collect proof summaries into ./_output/generated_results.html
# (Usually run automatically by gen_proofs but available here just in case)
# Run collect on the host: Docker Desktop macOS often returns EPERM on os.listdir() for bind-mounted ./_output.
docker-collect: docker-prepare-output
	python3 ./tools/collect --output=./_output/generated_results.html ./_output/

# Open an interactive shell inside the container for debugging
docker-shell: docker-prepare-output
	docker compose run --rm tamarin bash

# Launch Tamarin interactive mode in Docker. Access the GUI at http://127.0.0.1:$(PORT)
# Use with: make docker-web [type=EB|PM] [PORT=3001]
PORT ?= 3001
docker-web: docker-prepare-output
	docker compose run --rm -p $(PORT):3001 -e type=$(type) tamarin sh -c 'make preprocess && ./tools/tamarin-prover interactive generated_$${type}.spthy'

# Launch Tamarin interactive mode over all proofs in output/. Requires gen_proofs first.
# Access at http://127.0.0.1:$(PORT)
docker-web-proofs: docker-prepare-output
	docker compose run --rm -p $(PORT):3001 tamarin ./tools/tamarin-prover interactive ./_output/

