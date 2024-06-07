## About
HMDroidBot is a lightweight test input generator for HarmonyOS. It forks from [Droidbot](https://github.com/honeynet/droidbot) and supports HarmonyOS devices.
It can send random or scripted input events to an HarmonyOS app, achieve higher test coverage more quickly, and generate a UI transition graph (UTG) after testing.

## Prerequisite

1. `Python3`
2. `HDC cmdtool`

## How to install

Clone this repo and install with `pip`:

```shell
git clone 
cd droidbot/
pip install -e .
```

If successfully installed, you should be able to execute `droidbot -h`.

## How to use

1. Make sure you have:

    + `.hap` file path of the app you want to analyze.
    + A device or an emulator connected to your host machine via `hdc`.

2. Start HMDroidBot:

    ```
    droidbot -a <path_to_hap> -o output_dir -is_harmonyos
    ```
    That's it! You will find much useful information, including the UTG, generated in the output dir.

    + If you are using multiple devices, you may need to use `-d <device_serial>` to specify the target device. The easiest way to determine a device's serial number is calling `hdc list targets`.
    + You may find other useful features in `droidbot -h`.

## Acknowledgement

1. [Droidbot](https://github.com/honeynet/droidbot)
