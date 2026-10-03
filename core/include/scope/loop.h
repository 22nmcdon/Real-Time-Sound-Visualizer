// The two numbers the picture's loop shares across the core: the phosphor
// grid's size, which the score reads and the picture's sources write, and how
// far a source reading the picture may move a control, which the hearing's
// sources take too while they hear the generator. Here once, so the headers
// that need them can be included together.
#pragma once

namespace scope {

constexpr int kPhosphorN = 64;          // PHOSPHOR_N: the grid is 64 by 64
constexpr double kPhotoReach = 0.5;     // PHOTO_REACH: the most of a span the picture may move a control

}  // namespace scope
