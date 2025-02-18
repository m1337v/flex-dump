# Flex-Dump: A Header Conversion Tool for Flex 3

Flex-Dump is a Python tool designed to convert class-dumped headers from iOS frameworks into a format suitable for Flex 3 patches. By automating the conversion process, it simplifies the creation and modification of Flex 3 patches for developers and enthusiasts.

---
## 🚀 How to Use the Script

### **Step 1: Dump Headers Using class-dumpc**

1. **Download class-dumpc** from this [release](https://github.com/lechium/classdumpios/releases/tag/4.2.0-RELEASE1).
2. **Open a terminal** and run the following command:
   
   ```sh
   ./class-dumpc -H <drag in the framework binary> -o <output directory>
   ```

   **Example:**
   ```sh
   ./class-dumpc -H /path/to/GoogleInteractiveMediaAds.framework/GoogleInteractiveMediaAds -o /path/to/output/GoogleInteractiveMediaAds.framework
   ```

   ✅ Ensure the output directory has the same name as the framework, e.g., `GoogleInteractiveMediaAds.framework`.
   ✅ All headers should now be dumped into the specified directory.

---
### **Step 2: Run the Flex-Dump Script**

1. **Ensure you have Python 3 installed**, then navigate to the directory where the script is located and run:
   
   ```sh
   python3 convert_headers_to_extracted.py
   ```

2. **When prompted, enter the name of the framework** (without the `.framework` extension). Example:
   
   ```
   GoogleInteractiveMediaAds
   ```

3. **Drag and drop the entire framework folder** (e.g., `GoogleInteractiveMediaAds.framework`, which contains all the headers) into the script when prompted.
4. The script will generate a `.extracted` file named after the framework.

---
### **Step 3: Copy the Extracted File to Flex 3 Directory**

1. **Move the generated `.extracted` file** to the following directory:
   
   ```sh
   /var/mobile/Documents/Flex
   ```

2. **Open Flex 3**, and the new library should appear under the **“Embedded Libraries”** section.

---
## 📌 Current Status

🚧 **Early Development:** This tool is in its early stages and may contain bugs or incomplete functionality. Community contributions are highly encouraged to improve its reliability and feature set.

---
## ✨ Features

✅ **Header Conversion:** Converts headers dumped using `class-dumpc`.
✅ **Flex 3 Compatibility:** Simplifies header preparation for Flex 3 patches.
✅ **Minimal Dependencies:** Easy to run with a simple setup.

---
## 🤝 How You Can Help

We welcome contributions to fix bugs, improve conversion accuracy, and expand functionality. Here’s how you can help:

1. **Submit Issues:** Report bugs or suggest improvements.
2. **Fork & Pull Requests:** Fix bugs or add features and submit pull requests.
3. **Testing:** Test the tool on different frameworks and share your feedback.

Thank you for your support in making Flex-Dump better for everyone! 🚀

