class Bbc < Formula
  include Language::Python::Virtualenv

  desc "Bitter Brain Context - AI Assistant Context Manager"
  homepage "https://github.com/Anubis44197/BBC-SON-SURUM"
  url "https://github.com/Anubis44197/BBC-SON-SURUM/archive/refs/tags/v8.3.0.tar.gz"
  sha256 "5c2e73f3e7fb873eb891feb5a6e5e7bb8a328cbbd1a8f4cc34ee2503ae925413"
  license "MIT"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "BBC Master CLI", shell_output("#{bin}/bbc --help")
  end
end
