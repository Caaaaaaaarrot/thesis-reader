#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <queue>
#include <vector>

#ifdef _WIN32
#define TR_API extern "C" __declspec(dllexport)
#else
#define TR_API extern "C" __attribute__((visibility("default")))
#endif

namespace {
struct Node {
    std::array<int, 256> next;
    int fail = 0;
    std::vector<std::size_t> matches;
    Node() { next.fill(-1); }
};

struct Matcher {
    std::vector<Node> nodes{1};
    std::vector<std::size_t> lengths;
};
}

TR_API int tr_abi_version() { return 1; }

// UTF-8 byte matching; Unicode normalization/lowercasing remains in Python.
TR_API void* tr_create_matcher(const char* const* keywords,
                               const std::size_t* lengths, std::size_t count) noexcept {
    if (!keywords || !lengths || !count) return nullptr;
    Matcher* matcher = nullptr;
    try {
        matcher = new Matcher;
        matcher->lengths.assign(lengths, lengths + count);
        for (std::size_t k = 0; k < count; ++k) {
            if (!keywords[k] || !lengths[k]) { delete matcher; return nullptr; }
            int state = 0;
            for (std::size_t i = 0; i < lengths[k]; ++i) {
                const auto c = static_cast<unsigned char>(keywords[k][i]);
                int next = matcher->nodes[state].next[c];
                if (next == -1) {
                    next = static_cast<int>(matcher->nodes.size());
                    matcher->nodes.emplace_back();
                    matcher->nodes[state].next[c] = next;
                }
                state = next;
            }
            matcher->nodes[state].matches.push_back(k);
        }
        std::queue<int> pending;
        for (int c = 0; c < 256; ++c) {
            const int child = matcher->nodes[0].next[c];
            if (child == -1) matcher->nodes[0].next[c] = 0;
            else pending.push(child);
        }
        while (!pending.empty()) {
            const int state = pending.front();
            pending.pop();
            for (int c = 0; c < 256; ++c) {
                const int child = matcher->nodes[state].next[c];
                const int fallback = matcher->nodes[matcher->nodes[state].fail].next[c];
                if (child == -1) matcher->nodes[state].next[c] = fallback;
                else {
                    matcher->nodes[child].fail = fallback;
                    const auto& outputs = matcher->nodes[fallback].matches;
                    matcher->nodes[child].matches.insert(matcher->nodes[child].matches.end(), outputs.begin(), outputs.end());
                    pending.push(child);
                }
            }
        }
        return matcher;
    } catch (...) {
        delete matcher;
        return nullptr;
    }
}

// Immutable matcher, caller-owned result: safe for concurrent scoring calls.
// Count non-overlapping occurrences per keyword, matching Python str.count.
TR_API int tr_count_keywords(const void* handle, const char* const* texts,
                              const std::size_t* lengths, std::size_t page_count,
                              std::uint64_t* output) noexcept {
    if (!handle || !texts || !lengths || !output) return -1;
    try {
        const auto& matcher = *static_cast<const Matcher*>(handle);
        const std::size_t keyword_count = matcher.lengths.size();
        if (page_count > std::numeric_limits<std::size_t>::max() / keyword_count) return -1;
        std::fill(output, output + page_count * keyword_count, 0);
        std::vector<std::size_t> next_allowed(keyword_count);
        for (std::size_t p = 0; p < page_count; ++p) {
            if (!texts[p]) return -1;
            std::fill(next_allowed.begin(), next_allowed.end(), 0);
            int state = 0;
            for (std::size_t i = 0; i < lengths[p]; ++i) {
                state = matcher.nodes[state].next[static_cast<unsigned char>(texts[p][i])];
                for (const auto keyword : matcher.nodes[state].matches) {
                    const auto end = i + 1;
                    const auto start = end - matcher.lengths[keyword];
                    if (start >= next_allowed[keyword]) {
                        ++output[p * keyword_count + keyword];
                        next_allowed[keyword] = end;
                    }
                }
            }
        }
        return 0;
    } catch (...) { return -1; }
}

TR_API void tr_destroy_matcher(void* handle) noexcept {
    delete static_cast<Matcher*>(handle);
}
