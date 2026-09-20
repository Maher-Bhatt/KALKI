def main():
    with open('app/ui/base.css', 'r', encoding='utf-8') as f:
        content = f.read()

    style = """
/* Success Animation */
.btn.is-success {
  background: var(--success, #2da44e) !important;
  color: #fff !important;
  border-color: transparent !important;
  transition: background 0.2s ease, color 0.2s ease;
}
[data-motion="off"] .btn.is-success { transition: none; }
@media (prefers-reduced-motion: reduce) { .btn.is-success { transition: none; } }
"""
    if "is-success" not in content:
        content += style
        with open('app/ui/base.css', 'w', encoding='utf-8') as f:
            f.write(content)
        print("base.css patched")

if __name__ == "__main__":
    main()
