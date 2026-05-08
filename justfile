default:
    @just --list

install:
    uv tool install -e .
    mkdir -p ~/.config/transcribe
    @if [ ! -f ~/.config/transcribe/config.ini ]; then \
        cp config.example.ini ~/.config/transcribe/config.ini; \
        echo "Created ~/.config/transcribe/config.ini"; \
    else \
        echo "Config already exists, skipping."; \
    fi
    @if [ ! -f ~/.config/transcribe/hotwords.txt ]; then \
        cp hotwords.example.txt ~/.config/transcribe/hotwords.txt; \
        echo "Created ~/.config/transcribe/hotwords.txt"; \
    else \
        echo "Hotwords file already exists, skipping."; \
    fi

restart:
    transcribe -r

hotwords:
    fresh ~/.config/transcribe/hotwords.txt
    just restart

test:
    transcribe --test

test-reuse:
    transcribe --test --reuse-recording

update: install

uninstall:
    uv tool uninstall transcribe
    @echo "Note: config files in ~/.config/transcribe/ were not removed."
