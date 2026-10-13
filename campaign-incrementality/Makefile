.PHONY: install test lint run all study clean history diagnose assets sensitivity

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/ studies/

run:            ## headline cohort, full exhibits
	python -m incrementality run configs/mid_year_sale_2025.yaml -v

all:            ## every cohort in configs/
	python -m incrementality all -v

study:          ## Monte Carlo accuracy study: effect arm and zero-effect arm (slow)
	python studies/recovery_study.py --arm effect --seeds 0-11
	python studies/recovery_study.py --arm zero_effect --seeds 0-25

history:        ## does a longer history fix the Black Friday error? (slow)
	python studies/history_length_study.py --seeds 301-306

clean:
	rm -rf outputs/figures/*.png outputs/tables/*.csv outputs/*.md
	find . -name __pycache__ -type d -exec rm -rf {} +

sensitivity:    ## assumption sensitivity sweeps (slow)
	python studies/assumption_sensitivity.py --sweep leakage --seeds 0-3
	python studies/assumption_sensitivity.py --sweep repeat --seeds 0-3

diagnose:       ## model adequacy, power, design comparison
	python -m incrementality diagnose configs/mid_year_sale_2025.yaml

assets:         ## regenerate hero banner and methodology diagram
	python -m incrementality assets configs/mid_year_sale_2025.yaml
