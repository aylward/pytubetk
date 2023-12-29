import os

import itk
import numpy as np
from itk import TubeTK as tube


class segment_vessels_brain_mra:
    """
    Extract tubespatialobject representations of the vessels in a
    MR angiogram in which the skull has been stripped, leaving on the
    brain.
    """

    def __init__(self, debug=False, debug_output_base_name="./Debug/out"):
        self.debug = debug
        self.debug_output_base_name = debug_output_base_name
        dname = os.path.dirname(self.debug_output_base_name)
        if not os.path.exists(dname):
            os.makedirs(dname)

        self.vessels_scale = 1.0

        self.intensity_z_score_range = 10

        self.num_training_seeds = 50
        self.num_seeds = 1000
        self.min_vessel_length = 500

        self.data_im = itk.Image[itk.F, 3].New()
        self.data_array = type(np.array)
        self.data_norm_im = itk.Image[itk.F, 3].New()
        self.data_norm_array = type(np.array)
        self.data_mask = itk.Image[itk.F, 3].New()
        self.data_mask_erode = itk.Image[itk.F, 3].New()

        self.spacing = 1

        self.training_seed_coord = []
        self.training_mask_image = itk.Image[itk.F, 3].New()

        self.vessels_enhancement_scales = [0.5, 0.75, 1.25, 2.0, 3.0]

        self.data_vessels_enhanced_im = itk.Image[itk.F, 3].New()
        self.data_vessels_im = itk.Image[itk.F, 3].New()
        self.data_vessels_group = itk.GroupSpatialObject[3].New()

    def set_input_image(self, data_im):
        """
        Provide the volumetic image to be processed.

        Args:
            data_im: the MR angiogram brain-only image.
        """
        print("initializing image", flush=True)

        self.data_im = data_im
        self.data_array = itk.GetArrayFromImage(self.data_im)

        imMath = tube.ImageMath.New(self.data_im)
        imMath.Threshold(1, 99999, 1, 0)
        self.data_mask = imMath.GetOutput()
        imMath.Erode(10, 1, 0)
        self.data_mask_erode = imMath.GetOutput()

        self.spacing = self.data_im.GetSpacing()[0]

        if self.debug:
            print("Saving mask image", flush=True)
            itk.imwrite(
                self.data_mask_erode,
                self.debug_output_base_name + "-DataMaskErode.mha",
            )

    def normalize_image(self, vessels_scale: float = -1):
        """
        Use image statistics to rescale the image to 0 to 100.

        Args:
            vessels_scale: scale factor for default range of vessels
                to be extracted.  Default = 1.0. Scale of 0.25 will
                favor smaller vessels.  Scale of 2.0 will favor larger
                vessels.
        """
        print("Normalizing image", flush=True)

        if vessels_scale > 0:
            self.vessels_scale = vessels_scale
        imMath = tube.ImageMath.New(self.data_im)
        imMath.Blur(self.spacing * self.vessels_scale)
        imMath.ReplaceValuesOutsideMaskRange(self.data_mask, 1, 1, 0)
        imBlur = imMath.GetOutput()

        data_norm = itk.GetArrayFromImage(imBlur)
        data_norm_nz_indx = np.nonzero(self.data_array)
        data_norm_nz = data_norm[data_norm_nz_indx]
        self.data_mean = np.mean(data_norm_nz)
        self.data_stddev = np.std(data_norm_nz)

        print("data stats =", self.data_mean, self.data_stddev, flush=True)
        data_norm = np.where(
            data_norm > 0,
            (
                (
                    (data_norm - self.data_mean)
                    / (self.data_stddev * (1.5 * self.intensity_z_score_range))
                )
                + 0.5
            )
            / 2.0,
            0,
        )
        data_norm = np.where(data_norm > 1, 1.0, data_norm)
        data_norm = np.where(data_norm < 0, 0.0, data_norm)
        self.data_norm_min = data_norm.min()
        self.data_norm_max = data_norm.max()
        print("data =", self.data_norm_min, self.data_norm_max, flush=True)
        self.data_norm_array = (
            (data_norm - self.data_norm_min)
            / (self.data_norm_max - self.data_norm_min)
            * 100
        )
        self.data_norm_im = itk.GetImageFromArray(self.data_norm_array)
        self.data_norm_im.CopyInformation(self.data_im)

        if self.debug:
            print("Saving normalized image", flush=True)
            itk.imwrite(
                self.data_norm_im,
                self.debug_output_base_name
                + "_VS"
                + str(self.vessels_scale)
                + "-Normalized.mha",
            )

    def _normalize_second_image(self, data_im2):
        """
        Internal member function to applying consistent statistics (from
            input image) to other images.

        Args:
            data_im2: an image to be normalized using same stats as
                input_image
        """
        imMath = tube.ImageMath.New(data_im2)
        imMath.Blur(self.spacing * self.vessels_scale)
        imBlur = imMath.GetOutput()

        data_norm2 = itk.GetArrayFromImage(imBlur)
        data_norm2 = (
            (
                (data_norm2 - self.data_mean)
                / (self.data_stddev * (1.5 * self.intensity_z_score_range))
            )
            + 0.5
        ) / 2.0

        data_norm2 = np.where(data_norm2 > 1, 1.0, data_norm2)
        data_norm2 = np.where(data_norm2 < 0, 0.0, data_norm2)

        data_norm2_array = (
            (data_norm2 - self.data_norm_min)
            / (self.data_norm_max - self.data_norm_min)
            * 100
        )

        data_norm2_im = itk.GetImageFromArray(data_norm2_array)
        data_norm2_im.CopyInformation(self.data_im)

        itk.imwrite(
            data_norm2_im,
            self.debug_output_base_name
            + "-alter_VS"
            + str(self.vessels_scale)
            + "-Normalized.mha",
        )

        return data_norm2_im

    def identify_training_seeds(self, num_training_seeds=0):
        print("Identifying training seeds", flush=True)

        if num_training_seeds != 0:
            self.num_training_seeds = num_training_seeds
        seed_coverage = 10
        data_min = self.data_norm_array.min()
        self.training_seed_coord = np.zeros([self.num_training_seeds, 3])
        for i in range(self.num_training_seeds):
            self.training_seed_coord[i] = np.unravel_index(
                np.argmax(self.data_norm_array, axis=None),
                self.data_norm_array.shape,
            )
            indx = [
                int(self.training_seed_coord[i][0]),
                int(self.training_seed_coord[i][1]),
                int(self.training_seed_coord[i][2]),
            ]
            minX = max(indx[0] - seed_coverage, 0)
            maxX = min(indx[0] + seed_coverage, self.data_norm_array.shape[0])
            minY = max(indx[1] - seed_coverage, 0)
            maxY = min(indx[1] + seed_coverage, self.data_norm_array.shape[1])
            minZ = max(indx[2] - seed_coverage, 0)
            maxZ = min(indx[2] + seed_coverage, self.data_norm_array.shape[2])
            self.data_norm_array[minX:maxX, minY:maxY, minZ:maxZ] = data_min
            indx.reverse()
            self.training_seed_coord[:][
                i
            ] = self.data_norm_im.TransformIndexToPhysicalPoint(indx)
            print(
                self.training_seed_coord[:][i],
                ":",
                np.max(self.data_norm_array, axis=None),
            )

    def generate_training_mask_image(self):
        print("Generating training mask", flush=True)

        # Manually extract a few vessels to form an
        #     image-specific training set
        print("   - Extracting training vessels", flush=True)
        vSeg = tube.SegmentTubes.New(Input=self.data_norm_im)
        vSeg.SetVerbose(True)
        vSeg.SetMinRoundness(0.1)
        vSeg.SetMinRidgeness(0.8)
        vSeg.SetMinCurvature(0.000001)
        # MinCurvature is the most influential variable
        vSeg.SetRadiusInObjectSpace(1.5)
        vSeg.SetMinLength(300)
        for i in range(self.num_training_seeds):
            print("     Seed", i, "of", self.num_training_seeds, flush=True)
            vSeg.ExtractTubeInObjectSpace(self.training_seed_coord[i], i)
        imMath = tube.ImageMath.New(vSeg.GetTubeMaskImage())
        imMath.Threshold(0, 0, 0, 1)
        vessels_mask_image = imMath.GetOutput()
        if self.debug:
            itk.imwrite(
                vessels_mask_image,
                self.debug_output_base_name
                + "_VS"
                + str(self.vessels_scale)
                + "-VesselsTraining.mha",
            )

        print(
            "   - Computing training mask (This takes several minutes)",
            flush=True,
        )
        trMask = tube.ComputeTrainingMask.New(Input=vessels_mask_image)
        trMask.SetGap(10)
        trMask.SetObjectWidth(1)
        trMask.SetNotObjectWidth(1)
        trMask.Update()
        tmpIm = trMask.GetOutput()
        tmpIm.CopyInformation(self.data_im)
        imMath.SetInput(tmpIm)
        imMath.ReplaceValuesOutsideMaskRange(self.data_mask_erode, 1, 1, 0)
        self.training_mask_image = imMath.GetOutput()
        if self.debug:
            itk.imwrite(
                self.training_mask_image,
                self.debug_output_base_name
                + "_VS"
                + str(self.vessels_scale)
                + "-VesselsTrainingMask.mha",
            )

    def enhance_vessels(self):
        print("Enhancing vessels (This takes several minutes)", flush=True)
        ImageType = itk.Image[itk.F, 3]

        enhancer = tube.EnhanceTubesUsingDiscriminantAnalysis[
            ImageType, ImageType  # LabelMapType
        ].New()
        enhancer.AddInput(self.data_norm_im)
        enhancer.SetLabelMap(self.training_mask_image)
        enhancer.SetRidgeId(255)
        enhancer.SetBackgroundId(128)
        enhancer.SetUnknownId(0)
        enhancer.SetTrainClassifier(True)
        enhancer.SetUseIntensityOnly(True)
        enhancer.SetUseFeatureMath(True)
        scales = (
            np.array(self.vessels_enhancement_scales)
            * self.vessels_scale
            * self.spacing
        )
        enhancer.SetScales(scales)
        enhancer.Update()
        enhancer.ClassifyImages()

        imMath = tube.ImageMath.New(enhancer.GetClassProbabilityImage(0))
        imMath.Blur(0.5 * self.spacing * self.vessels_scale)
        prob0 = imMath.GetOutput()
        imMath.SetInput(enhancer.GetClassProbabilityImage(1))
        imMath.Blur(0.5 * self.spacing * self.vessels_scale)
        prob1 = imMath.GetOutput()

        imDiff = itk.SubtractImageFilter.New(Input1=prob0, Input2=prob1)
        imDiff.Update()
        imDiffArr = itk.GetArrayFromImage(imDiff.GetOutput(0))
        dMax = imDiffArr.max()
        imProbArr = imDiffArr / dMax
        tmp_im = itk.GetImageFromArray(imProbArr)
        tmp_im.CopyInformation(self.data_im)
        imMath.SetInput(tmp_im)
        imMath.ReplaceValuesOutsideMaskRange(self.data_mask, 1, 1, 0)
        self.data_vessels_enhanced_im = imMath.GetOutput()
        if self.debug:
            itk.imwrite(
                self.data_vessels_enhanced_im,
                self.debug_output_base_name
                + "_VS"
                + str(self.vessels_scale)
                + "-VesselsEnhanced.mha",
            )

    def extract_vessels(self, alter_image=None):
        print("Extract vessels (This takes several minutes)", flush=True)

        if alter_image == None:
            input_image = self.data_norm_im
        else:
            input_image = self._normalize_second_image(alter_image)

        imMath = tube.ImageMath.New(self.data_vessels_enhanced_im)
        # imMath.MedianFilter(1)
        imMath.Threshold(0.0000000001, 10000, 1, 0)
        imMath.ReplaceValuesOutsideMaskRange(self.data_mask_erode, 1, 1, 0)
        imVessMask = imMath.GetOutputShort()
        itk.imwrite(imVessMask, "imVessMask.mha")

        ccSeg = tube.SegmentConnectedComponents.New(imVessMask)
        ccSeg.SetMinimumVolume(50)
        ccSeg.Update()
        tmp_im = ccSeg.GetOutput()
        imMathSS = tube.ImageMath.New(tmp_im)
        imMathSS.Threshold(1, 9999999, 1, 0)
        imVessMask = imMathSS.GetOutput()
        if self.debug:
            itk.imwrite(
                imVessMask,
                self.debug_output_base_name
                + "_VS"
                + str(self.vessels_scale)
                + "-VesselSeedsInitialMask.mha",
            )
        tmpVessMask = itk.GetArrayFromImage(imVessMask).astype(np.float32)
        imVessMask = itk.GetImageFromArray(tmpVessMask)
        imVessMask.CopyInformation(self.data_im)

        print("   - Extracting seed info", flush=True)
        imMath.SetInput(self.data_vessels_enhanced_im)
        imMath.ReplaceValuesOutsideMaskRange(imVessMask, 1, 1, 0)
        imSeeds = imMath.GetOutput()

        imMath.SetInput(imVessMask)
        imMath.Threshold(1, 1, 0, 1)
        imVessMaskInv = imMath.GetOutput()
        distFilter = itk.DanielssonDistanceMapImageFilter.New(
            Input=imVessMaskInv
        )
        distFilter.Update()
        imSeedsRadius = distFilter.GetOutput(0)

        if self.debug:
            itk.imwrite(
                imSeedsRadius,
                self.debug_output_base_name
                + "_VS"
                + str(self.vessels_scale)
                + "-VesselSeedsRadius.mha",
            )

        # Eleminate the centers of large blobs as seeds
        imMath.SetInput(imSeeds)
        imMath.ReplaceValuesOutsideMaskRange(
            imSeedsRadius,
            0,
            self.spacing * self.vessels_enhancement_scales[-1] * 2,
            0,
        )
        imSeeds = imMath.GetOutput()
        if self.debug:
            itk.imwrite(
                imSeeds,
                self.debug_output_base_name
                + "_VS"
                + str(self.vessels_scale)
                + "-VesselSeeds.mha",
            )

        if self.debug:
            itk.imwrite(
                input_image,
                self.debug_output_base_name
                + "_VS"
                + str(self.vessels_scale)
                + "-VesselInput.mha",
            )

        print("   - Extracting vessels", flush=True)
        vSeg = tube.SegmentTubes.New(Input=input_image)
        vSeg.SetVerbose(True)
        vSeg.SetMinCurvature(0.001)
        vSeg.SetMinRoundness(0.1)
        vSeg.SetMinRidgeness(0.1)
        vSeg.SetMinLevelness(0.001)
        vSeg.SetMinLength(self.min_vessel_length)
        # vSeg.SetRadiusInObjectSpace( 1.5 )
        vSeg.SetBorderInIndexSpace(3)
        vSeg.SetSeedMask(imSeeds)
        vSeg.SetSeedRadiusMask(imSeedsRadius)
        vSeg.SetOptimizeRadius(True)
        vSeg.SetSeedMaskMaximumNumberOfPoints(self.num_seeds)
        vSeg.SetUseSeedMaskAsProbabilities(True)
        vSeg.SetSeedExtractionMinimumProbability(0.1)
        vSeg.ProcessSeeds()
        self.data_vessels_im = vSeg.GetTubeMaskImage()

        if self.debug:
            print("   - Saving results", flush=True)
            itk.imwrite(
                self.data_vessels_im,
                self.debug_output_base_name
                + "_VS"
                + str(self.vessels_scale)
                + "-Vessels.mha",
            )

        TubeMath = tube.TubeMath[3, itk.F].New()
        TubeMath.SetInputTubeGroup(vSeg.GetTubeGroup())
        TubeMath.SetUseAllTubes()
        TubeMath.SmoothTube(4, "SMOOTH_TUBE_USING_INDEX_GAUSSIAN")
        TubeMath.SmoothTubeProperty(
            "Radius", 2, "SMOOTH_TUBE_USING_INDEX_GAUSSIAN"
        )
        self.data_vessels_group = TubeMath.GetOutputTubeGroup()

        if self.debug:
            SOWriter = itk.SpatialObjectWriter[3].New()
            SOWriter.SetInput(self.data_vessels_group)
            SOWriter.SetBinaryPoints(False)
            SOWriter.SetFileName(
                self.debug_output_base_name
                + "_VS"
                + str(self.vessels_scale)
                + "-Vessels.tre"
            )
            SOWriter.Update()

    def run(self, vessels_scale=1.5, alter_image=None):
        self.normalize_image(vessels_scale=vessels_scale)
        self.identify_training_seeds()
        self.generate_training_mask_image()
        self.enhance_vessels()
        self.extract_vessels(alter_image=alter_image)
