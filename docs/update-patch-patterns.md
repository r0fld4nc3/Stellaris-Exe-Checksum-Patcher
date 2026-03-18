# Update patch patterns

## Understanding patterns.json

`patch_pattern` is the pattern of bytes the patcher will look for when determining where to apply the patch.

- Sections like `.{8}` mean 8 bytes of anything
- `%s` is where the bytes to replace will be; they must match `hex_find`
- The `hex_find` bytes will be replaced with `hex_replace`

## Prerequisites

[Ghidra](github.com/NationalSecurityAgency/ghidra)

## Linux

#### Checksum pattern

1. Open the Stellaris binary in Ghidra
1. Go to _Functions_ and search for `InitGame`
1. Double-click the first instance of _InitGame_ to go to it in the _Decompile_ view
1. Make sure the function is `CGameApplication::InitGame` (There are multiple InitGame functions)
1. Search the function for `CChecksum::GetDataChkSum` and click the line to highlight it
1. Look at the _Listing_ on the left starting from the highlighted instruction
1. Make sure there's a `TEST EBX,EBX` (`85 db`) instruction within the next 10 instructions or so
1. Look at the instructions just above `TEST EBX,EBX` and confirm they match the `Checksum` pattern in [patterns.json](../src/patch_patterns/patterns.json)
1. If not, update `patch_pattern` as necessary

#### Warning pattern

1. Go to _Functions_ and search for `ApplyVersionToTextBox`
1. Double-click the function name to go to it in the _Decompile_ view
1. Search the function for `CChecksum::GetDataChkSum` and click the line to highlight it
1. Look at the _Listing_ on the left starting from the highlighted instruction
1. Make sure there's a `TEST EAX,EAX` (`85 c0`) instruction within the next 10 instructions or so
1. Look at the instructions just above `TEST EAX,EAX` and confirm they match the `Warning` pattern in [patterns.json](../src/patch_patterns/patterns.json)
1. If not, update `patch_pattern` as necessary

#### Tooltip pattern

1. Go to _Strings_ and search for `ACHIEVEMENT_TOOLTIP_CHECKSUM`
1. Double-click the search result to load it in the Listing
1. In _Listing_ on the left, right-click the highlighted result > _References_ > _Show References to Address_
1. In the _References to_ window, double click the result
1. The reference should be highlighted in _Listing_ on the left
1. Look at the _Listing_ on the left starting from the highlighted instruction
1. Make sure there's a `TEST EAX,EAX` (`85 c0`) instruction within the **previous** 10 instructions or so
1. Look at the instructions just above `TEST EAX,EAX` and confirm they match the `Tooltip Patch` pattern in [patterns.json](../src/patch_patterns/patterns.json)
1. If not, update `patch_pattern` as necessary

## Windows

https://steamcommunity.com/sharedfiles/filedetails/?id=2460079052