"""
Generate an image containing only the interior of the skull.

Takes one or more images as input. One is designated as the "target"
which will be returned skullstripped. One is the "anatomy" image that
will be registered with a collection of pre-segmented data for
atlas-based segmentation. The atlas images are registered, the
skull-stripped atlas images are then used to create a refined registration,
and then the image is re-skull stripped. Parzen statistics and
morphological operations drive the skull stripping.

The atlas cases should be in the pytubetk/data directory.  See that
directory for download info.
"""

import os

import itk
from itk import TubeTK as tube


class strip_skull:
    """Generate an image containing only the interior of the skull."""

    def __init__(self, data_dir="../data/MRI-Normals", debug=False):
        """
        Create an instance of the skull stripping method.

        args:
            debug - save intermediate results to a "Debug" directory.
        """
        self.debug = debug

        self.ImageType = itk.Image[itk.F, 3]
        self.LabelMapType = itk.Image[itk.UC, 3]

        self.input_images = []
        self.input_images_reg = []
        self.brain_image = []
        self.anatomic_brain_image = []

        self.cohort_list = [
            ["Normal003-FLASH.mha", "Normal003-FLASH-Brain.mha"],
            ["Normal010-FLASH.mha", "Normal010-FLASH-Brain.mha"],
            ["Normal026-FLASH.mha", "Normal026-FLASH-Brain.mha"],
            ["Normal034-FLASH.mha", "Normal034-FLASH-Brain.mha"],
            ["Normal045-FLASH.mha", "Normal045-FLASH-Brain.mha"],
            ["Normal056-FLASH.mha", "Normal056-FLASH-Brain.mha"],
            ["Normal063-FLASH.mha", "Normal063-FLASH-Brain.mha"],
            ["Normal071-FLASH.mha", "Normal071-FLASH-Brain.mha"],
        ]
        self.cohort_blur = 2
        self.cohort_reg = []
        self.cohort_regB = []

        self.data_dir = data_dir


    def set_input_images(self, images):
        """
        List of itk images (MRI) that combine to make skull stripping.

        Images should nominally be MRI.  They will be registered to the 0th.
        """
        self.input_images = images
        self.brain_image = []
        self.anatomic_brain_image = []

    def register_input_images(self, target_image_num=0):
        """
        Align the input images with the "target" input image.

        Args:
            target_image_num: the image to which all are registered.
        """
        if len(self.input_images) == 0:
            print("ERROR: Set input images first")
            return

        res = tube.ResampleImage.New(Input=self.input_images[target_image_num])
        res.SetMakeHighResIso(True)
        res.Update()
        self.input_images_reg = [res.GetOutput()]

        for img_num in range(1, len(self.input_images)):
            imReg = tube.RegisterImages[self.ImageType].New()
            imReg.SetFixedImage(self.input_images_reg[0])
            imReg.SetMovingImage(self.input_images[img_num])
            imReg.SetReportProgress(True)
            imReg.SetExpectedOffsetMagnitude(40)
            imReg.SetExpectedRotationMagnitude(0.01)
            imReg.SetExpectedScaleMagnitude(0.01)
            imReg.SetRigidMaxIterations(500)
            imReg.SetRigidSamplingRatio(0.1)
            imReg.SetRegistration("RIGID")
            imReg.SetMetric("MATTES_MI_METRIC")
            imReg.Update()
            self.input_images_reg.append(imReg.GetFinalMovingImage())

    def register_cohort(self, anatomic_image_num=1):
        """
        Register the atlas (8 pre-segmented normals) to the input.

        The input "anatomic" image is used to register with the normals.
        The anatomic image should have the most anatomic detail,
        to simplify registration.

        Args:
            anatomic_image_num: Defaults to image 1 (or 0 if only 1 input)
        """
        sample_file = os.path.join(self.data_dir, self.cohort_list[0][0])
        if not os.path.exists(sample_file):
            print(f"ERROR: Data file {sample_file} not found.  See data_download.sh for download info.")
            return

        N = len(self.cohort_list)
        cohort_base = []
        cohort_baseB = []
        for i in range(N):
            name = os.path.join(self.data_dir, self.cohort_list[i][0])
            nameB = os.path.join(self.data_dir, self.cohort_list[i][1])
            cohort_baseTmp = itk.imread(name, itk.F)
            cohort_baseBTmp = itk.imread(nameB, itk.F)
            cohort_base.append(cohort_baseTmp)
            cohort_baseB.append(cohort_baseBTmp)

        if anatomic_image_num >= len(self.input_images_reg):
            anatomic_image_num = len(self.input_images_reg) - 1
        imMath = tube.ImageMath.New(
            Input=self.input_images_reg[anatomic_image_num]
        )
        imMath.Blur(self.cohort_blur)
        input_blur = imMath.GetOutput()

        self.cohort_reg = []
        self.cohort_regB = []
        for i in range(N):
            imMath.SetInput(cohort_base[i])
            imMath.Blur(self.cohort_blur)
            cohort_baseBlur = imMath.GetOutput()
            regBTo1 = tube.RegisterImages[self.ImageType].New(
                FixedImage=input_blur, MovingImage=cohort_baseBlur
            )
            regBTo1.SetReportProgress(True)
            regBTo1.SetExpectedOffsetMagnitude(40)
            regBTo1.SetExpectedRotationMagnitude(0.01)
            regBTo1.SetExpectedScaleMagnitude(0.1)
            regBTo1.SetRigidMaxIterations(500)
            regBTo1.SetAffineMaxIterations(500)
            regBTo1.SetRigidSamplingRatio(0.05)
            regBTo1.SetAffineSamplingRatio(0.05)
            regBTo1.SetInitialMethodEnum("INIT_WITH_IMAGE_CENTERS")
            regBTo1.SetRegistration("PIPELINE_AFFINE")
            regBTo1.SetMetric("MATTES_MI_METRIC")
            regBTo1.Update()
            img = regBTo1.ResampleImage("LINEAR", cohort_base[i])
            self.cohort_reg.append(img)
            img = regBTo1.ResampleImage("LINEAR", cohort_baseB[i])
            self.cohort_regB.append(img)

    def refine_brain_registrations(self):
        """
        Refine the registrations using the brain-stripped atlas images.

        Given an intial cohort registration, re-register the skull-stripped
        version of them to the input anatomic image - ideally improving
        registration.
        """
        N = len(self.cohort_list)
        for i in range(N):
            if self.debug:
                print(f"*** Registration {i} ***")
            imMath = tube.ImageMath.New(Input=self.cohort_reg[i])
            imMath.ReplaceValuesOutsideMaskRange(self.cohort_regB[i], 1, 9999999, 0)
            cohort_brain_image = imMath.GetOutput()
            regBTo1 = tube.RegisterImages[self.ImageType].New(
                FixedImage=self.anatomic_brain_image,
                MovingImage=cohort_brain_image,
            )
            regBTo1.SetReportProgress(True)
            regBTo1.SetExpectedOffsetMagnitude(10)
            regBTo1.SetExpectedRotationMagnitude(0.005)
            regBTo1.SetExpectedScaleMagnitude(0.05)
            regBTo1.SetRigidMaxIterations(200)
            regBTo1.SetAffineMaxIterations(200)
            regBTo1.SetRigidSamplingRatio(0.05)
            regBTo1.SetAffineSamplingRatio(0.05)
            regBTo1.SetInitialMethodEnum("INIT_WITH_NONE")
            regBTo1.SetRegistration("PIPELINE_AFFINE")
            regBTo1.SetMetric("MATTES_MI_METRIC")
            regBTo1.Update()
            self.cohort_reg[i] = regBTo1.ResampleImage(
                "LINEAR", self.cohort_reg[i]
            )
            self.cohort_regB[i] = regBTo1.ResampleImage(
                "LINEAR", self.cohort_regB[i]
            )

    def segment_brain_using_registered_cohort(
        self, target_image_num=0, anatomic_image_num=1
    ):
        """
        Mask the inner skull (brain) region using the registered cohort.

        Once the cohort has been registered (and optionally refined), then
        use their segmented brains to estimate brain and background class
        statistics for the input images, and use those statistics and
        morphological operations to segment the brain.
        """
        if target_image_num >= len(self.input_images_reg):
            target_image_num = len(self.input_images_reg)-1
        if anatomic_image_num >= len(self.input_images_reg):
            anatomic_image_num = len(self.input_images_reg)-1
        self.cohort_regbrain = []
        N = len(self.cohort_list)
        for i in range(N):
            imMath = tube.ImageMath.New(Input=self.cohort_regB[i])
            imMath.Threshold(0, 1, 0, 1)
            img = imMath.GetOutput()
            if i == 0:
                imMathSum = tube.ImageMath.New(img)
                imMathSum.AddImages(img, 0, 1.0 / N)
                self.cohort_regbrain = imMathSum.GetOutput()
            else:
                imMathSum = tube.ImageMath.New(self.cohort_regbrain)
                imMathSum.AddImages(img, 1, 1.0 / N)
                self.cohort_regbrain = imMathSum.GetOutput()

        insideMath = tube.ImageMath.New(Input=self.cohort_regbrain)
        insideMath.Threshold(0.75, 1.0, 1, 0)
        insideMath.Erode(5, 1, 0)
        brainInside = insideMath.GetOutput()

        outsideMath = tube.ImageMath.New(Input=self.cohort_regbrain)
        outsideMath.Threshold(0, 0.75, 1, 0)
        outsideMath.Erode(5, 1, 0)
        brainOutsideAll = outsideMath.GetOutput()
        outsideMath.Erode(10, 1, 0)
        outsideMath.AddImages(brainOutsideAll, -1, 1)

        outsideMath.AddImages(brainInside, 1, 2)
        self.brain_training_mask = outsideMath.GetOutputUChar()

        segmenter = tube.SegmentConnectedComponentsUsingParzenPDFs[
            self.ImageType, self.LabelMapType
        ].New()
        segmenter.SetFeatureImage(self.input_images_reg[0])
        for i in range(1, len(self.input_images_reg)):
            segmenter.AddFeatureImage(self.input_images_reg[i])
        segmenter.SetInputLabelMap(self.brain_training_mask)
        segmenter.SetObjectId(2)
        segmenter.AddObjectId(1)
        segmenter.SetVoidId(0)
        segmenter.SetErodeDilateRadius(5)
        segmenter.Update()
        segmenter.ClassifyImages()
        brainCombinedMaskClassified = segmenter.GetOutputLabelMap()

        cast = itk.CastImageFilter[self.LabelMapType, self.ImageType].New()
        cast.SetInput(brainCombinedMaskClassified)
        cast.Update()
        self.brain_mask_raw = cast.GetOutput(0)

        brainMath = tube.ImageMath.New(Input=self.brain_mask_raw)
        brainMath.Threshold(2, 2, 1, 0)
        brainMath.Dilate(2, 1, 0)
        self.brain_mask = brainMath.GetOutput()
        brainMath.SetInput(self.input_images_reg[target_image_num])
        brainMath.ReplaceValuesOutsideMaskRange(self.brain_mask, 1, 1, 0)
        self.brain_image = brainMath.GetOutput()
        brainMath.SetInput(self.input_images_reg[anatomic_image_num])
        brainMath.ReplaceValuesOutsideMaskRange(self.brain_mask, 1, 1, 0)
        self.anatomic_brain_image = brainMath.GetOutput()

    def run(self, target_image_num=0, anatomic_image_num=1, use_iterative_refinement=False):
        """
        Execute the workflow of this class.

        Args:
            target_image_num: Image to be returned after skull stripping
            anatomic_image_num: Image to be used for atlas registrations
        """

        if self.debug:
            print("*** Set input images ***")
        self.register_input_images(target_image_num)

        if self.debug:
            print("*** Register cohort ***")
        self.register_cohort(anatomic_image_num)

        if self.debug:
            print("*** Initial brain segmentation ***")
        self.segment_brain_using_registered_cohort(
            target_image_num, anatomic_image_num
        )

        if use_iterative_refinement:
            if self.debug:
                itk.imwrite(self.anatomic_brain_image, "brain_initial_seg.mha")
                print("*** Refining registration ***") 
            self.refine_brain_registrations()

        if self.debug:
            print("*** Segment brain using registered cohort ***")
        self.segment_brain_using_registered_cohort(
            target_image_num, anatomic_image_num
        )

        return self.brain_image, self.anatomic_brain_image, self.brain_mask
