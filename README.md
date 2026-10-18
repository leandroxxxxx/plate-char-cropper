# PlateChar Annotator

A Python application for manually annotating and extracting individual license plate characters from images captured from videos.

## Objective

Simplify the creation of character-level datasets for training and evaluating artificial intelligence models, particularly for license plate recognition in surveillance camera footage.

## Planned Features

- Load images for annotation.
- Enter the license plate sequence before starting annotation.
- Display seven adjustable rectangles to select individual characters.
- Associate each rectangle with the corresponding character in the plate.
- Maintain the correct left-to-right character order.
- Automatically save individual character crops.
- Preserve the original image filename in the generated filenames.
- Append the corresponding character label to each output filename.
- Organize the extracted images for subsequent processing and AI model training.

## Filename Convention

For a license plate `ABC1D23` and a source image named `0001_video_00-01-23.450.png`, the extracted characters may be saved as follows:

```text
0001_video_00-01-23.450_A.png
0001_video_00-01-23.450_B.png
0001_video_00-01-23.450_C.png
0001_video_00-01-23.450_1.png
0001_video_00-01-23.450_D.png
0001_video_00-01-23.450_2.png
0001_video_00-01-23.450_3.png
```

This naming convention links each cropped image to its corresponding character while preserving information about the source image.

## Technologies

- Python
- Image processing and graphical interface libraries (to be determined).

## Project Status

Early development stage.

## License

To be determined.
