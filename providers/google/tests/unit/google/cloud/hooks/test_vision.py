#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

from unittest import mock

import pytest
from google.api_core.gapic_v1.method import DEFAULT
from google.cloud.vision_v1 import (
    AnnotateImageRequest,
    AnnotateImageResponse,
    EntityAnnotation,
    Feature,
    Product,
    ProductSearchClient,
    ProductSet,
    ReferenceImage,
    SafeSearchAnnotation,
)
from google.protobuf.json_format import MessageToDict

from airflow.exceptions import AirflowException
from airflow.providers.google.cloud.hooks.vision import ERR_DIFF_NAMES, ERR_UNABLE_TO_CREATE, CloudVisionHook
from airflow.providers.google.common.consts import CLIENT_INFO

from unit.google.cloud.utils.base_gcp_mock import mock_base_gcp_hook_default_project_id

PROJECT_ID_TEST = "project-id"
PROJECT_ID_TEST_2 = "project-id-2"
LOC_ID_TEST = "loc-id"
LOC_ID_TEST_2 = "loc-id-2"
PRODUCTSET_ID_TEST = "ps-id"
PRODUCTSET_ID_TEST_2 = "ps-id-2"
PRODUCTSET_NAME_TEST = f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}/productSets/{PRODUCTSET_ID_TEST}"
PRODUCT_ID_TEST = "p-id"
PRODUCT_ID_TEST_2 = "p-id-2"
PRODUCT_NAME_TEST = f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}/products/{PRODUCT_ID_TEST}"
PRODUCT_NAME = f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}/products/{PRODUCT_ID_TEST}"
REFERENCE_IMAGE_ID_TEST = "ri-id"
REFERENCE_IMAGE_GEN_ID_TEST = "ri-id"
ANNOTATE_IMAGE_REQUEST = {
    "image": {"source": {"image_uri": "gs://bucket-name/object-name"}},
    "features": [{"type": Feature.Type.LOGO_DETECTION}],
}
BATCH_ANNOTATE_IMAGE_REQUEST = [
    {
        "image": {"source": {"image_uri": "gs://bucket-name/object-name"}},
        "features": [{"type_": Feature.Type.LOGO_DETECTION}],
    },
    {
        "image": {"source": {"image_uri": "gs://bucket-name/object-name"}},
        "features": [{"type_": Feature.Type.LOGO_DETECTION}],
    },
]
REFERENCE_IMAGE_NAME_TEST = (
    f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}/products/"
    f"{PRODUCTSET_ID_TEST}/referenceImages/{REFERENCE_IMAGE_ID_TEST}"
)
REFERENCE_IMAGE_TEST = ReferenceImage(name=REFERENCE_IMAGE_GEN_ID_TEST)
REFERENCE_IMAGE_WITHOUT_ID_NAME = ReferenceImage()
DETECT_TEST_IMAGE = {"source": {"image_uri": "https://foo.com/image.jpg"}}
DETECT_TEST_ADDITIONAL_PROPERTIES = {"test-property-1": "test-value-1", "test-property-2": "test-value-2"}
LOCATION_PRODUCTSET_ID_TEST_PARAMS = [
    pytest.param(None, None, id="both-empty"),
    pytest.param(None, PRODUCTSET_ID_TEST, id="only-productset-id"),
    pytest.param(LOC_ID_TEST, None, id="only-location"),
]
LOCATION_PRODUCT_ID_TEST_PARAMS = [
    pytest.param(None, None, id="both-empty"),
    pytest.param(None, PRODUCT_ID_TEST, id="only-product-id"),
    pytest.param(LOC_ID_TEST, None, id="only-location"),
]


class TestGcpVisionHook:
    def setup_method(self):
        with mock.patch(
            "airflow.providers.google.cloud.hooks.vision.CloudVisionHook.__init__",
            new=mock_base_gcp_hook_default_project_id,
        ):
            self.hook = CloudVisionHook(gcp_conn_id="test")

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_credentials")
    @mock.patch("airflow.providers.google.cloud.hooks.vision.ProductSearchClient")
    def test_product_search_client_creation(self, mock_client, mock_get_creds):
        result = self.hook.get_conn()
        mock_client.assert_called_once_with(credentials=mock_get_creds.return_value, client_info=CLIENT_INFO)
        assert mock_client.return_value == result
        assert self.hook._client == result

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_create_productset_explicit_id(self, get_conn):
        # Given
        create_product_set_method = get_conn.return_value.create_product_set
        create_product_set_method.return_value = None
        parent = f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}"
        product_set = ProductSet()
        # When
        result = self.hook.create_product_set(
            location=LOC_ID_TEST,
            product_set_id=PRODUCTSET_ID_TEST,
            product_set=product_set,
            project_id=PROJECT_ID_TEST,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )

        # Then
        # ProductSet ID was provided explicitly in the method call above, should be returned from the method
        assert result == PRODUCTSET_ID_TEST
        create_product_set_method.assert_called_once_with(
            parent=parent,
            product_set=product_set,
            product_set_id=PRODUCTSET_ID_TEST,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_create_productset_autogenerated_id(self, get_conn):
        # Given
        autogenerated_id = "autogen-id"
        response_product_set = ProductSet(
            name=ProductSearchClient.product_set_path(PROJECT_ID_TEST, LOC_ID_TEST, autogenerated_id)
        )
        create_product_set_method = get_conn.return_value.create_product_set
        create_product_set_method.return_value = response_product_set
        parent = f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}"
        product_set = ProductSet()
        # When
        result = self.hook.create_product_set(
            location=LOC_ID_TEST, product_set_id=None, product_set=product_set, project_id=PROJECT_ID_TEST
        )
        # Then
        # ProductSet ID was not provided in the method call above. Should be extracted from the API response
        # and returned.
        assert result == autogenerated_id
        create_product_set_method.assert_called_once_with(
            parent=parent,
            product_set=product_set,
            product_set_id=None,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_create_productset_autogenerated_id_wrong_api_response(self, get_conn):
        # Given
        response_product_set = None
        create_product_set_method = get_conn.return_value.create_product_set
        create_product_set_method.return_value = response_product_set
        parent = f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}"
        product_set = ProductSet()
        # When
        with pytest.raises(AirflowException) as ctx:
            self.hook.create_product_set(
                location=LOC_ID_TEST,
                product_set_id=None,
                product_set=product_set,
                project_id=PROJECT_ID_TEST,
                retry=DEFAULT,
                timeout=None,
                metadata=(),
            )
        # Then
        # API response was wrong (None) and thus ProductSet ID extraction should fail.
        err = ctx.value
        assert "Unable to get name from response..." in str(err)
        create_product_set_method.assert_called_once_with(
            parent=parent,
            product_set=product_set,
            product_set_id=None,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_get_productset(self, get_conn):
        # Given
        name = ProductSearchClient.product_set_path(PROJECT_ID_TEST, LOC_ID_TEST, PRODUCTSET_ID_TEST)
        response_product_set = ProductSet(name=name)
        get_product_set_method = get_conn.return_value.get_product_set
        get_product_set_method.return_value = response_product_set
        # When
        response = self.hook.get_product_set(
            location=LOC_ID_TEST, product_set_id=PRODUCTSET_ID_TEST, project_id=PROJECT_ID_TEST
        )
        # Then
        assert response
        assert response == MessageToDict(response_product_set._pb)
        get_product_set_method.assert_called_once_with(name=name, retry=DEFAULT, timeout=None, metadata=())

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_update_productset_no_explicit_name(self, get_conn):
        # Given
        product_set = ProductSet()
        update_product_set_method = get_conn.return_value.update_product_set
        update_product_set_method.return_value = product_set
        productset_name = ProductSearchClient.product_set_path(
            PROJECT_ID_TEST, LOC_ID_TEST, PRODUCTSET_ID_TEST
        )
        # When
        result = self.hook.update_product_set(
            location=LOC_ID_TEST,
            product_set_id=PRODUCTSET_ID_TEST,
            product_set=product_set,
            update_mask=None,
            project_id=PROJECT_ID_TEST,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )
        # Then
        assert result == MessageToDict(product_set._pb)
        update_product_set_method.assert_called_once_with(
            product_set=ProductSet(name=productset_name),
            metadata=(),
            retry=DEFAULT,
            timeout=None,
            update_mask=None,
        )

    @pytest.mark.parametrize("location, product_set_id", LOCATION_PRODUCTSET_ID_TEST_PARAMS)
    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_update_productset_no_explicit_name_and_missing_params_for_constructed_name(
        self, get_conn, location, product_set_id
    ):
        # Given
        update_product_set_method = get_conn.return_value.update_product_set
        update_product_set_method.return_value = None
        product_set = ProductSet()
        # When
        with pytest.raises(AirflowException) as ctx:
            self.hook.update_product_set(
                location=location,
                product_set_id=product_set_id,
                product_set=product_set,
                update_mask=None,
                project_id=PROJECT_ID_TEST,
                retry=DEFAULT,
                timeout=None,
                metadata=(),
            )
        err = ctx.value
        assert err
        assert ERR_UNABLE_TO_CREATE.format(label="ProductSet", id_label="productset_id") in str(err)
        update_product_set_method.assert_not_called()

    @pytest.mark.parametrize("location, product_set_id", LOCATION_PRODUCTSET_ID_TEST_PARAMS)
    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_update_productset_explicit_name_missing_params_for_constructed_name(
        self,
        get_conn,
        location,
        product_set_id,
    ):
        # Given
        explicit_ps_name = ProductSearchClient.product_set_path(
            PROJECT_ID_TEST_2, LOC_ID_TEST_2, PRODUCTSET_ID_TEST_2
        )
        product_set = ProductSet(name=explicit_ps_name)
        update_product_set_method = get_conn.return_value.update_product_set
        update_product_set_method.return_value = product_set
        # When
        result = self.hook.update_product_set(
            location=location,
            product_set_id=product_set_id,
            product_set=product_set,
            update_mask=None,
            project_id=PROJECT_ID_TEST,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )
        # Then
        assert result == MessageToDict(product_set._pb)
        update_product_set_method.assert_called_once_with(
            product_set=ProductSet(name=explicit_ps_name),
            metadata=(),
            retry=DEFAULT,
            timeout=None,
            update_mask=None,
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_update_productset_explicit_name_different_from_constructed(self, get_conn):
        # Given
        update_product_set_method = get_conn.return_value.update_product_set
        update_product_set_method.return_value = None
        explicit_ps_name = ProductSearchClient.product_set_path(
            PROJECT_ID_TEST_2, LOC_ID_TEST_2, PRODUCTSET_ID_TEST_2
        )
        product_set = ProductSet(name=explicit_ps_name)
        template_ps_name = ProductSearchClient.product_set_path(
            PROJECT_ID_TEST, LOC_ID_TEST, PRODUCTSET_ID_TEST
        )
        # When
        # Location and product_set_id are passed in addition to a ProductSet with an explicit name,
        # but both names differ (constructed != explicit).
        # Should throw AirflowException in this case.
        with pytest.raises(AirflowException) as ctx:
            self.hook.update_product_set(
                location=LOC_ID_TEST,
                product_set_id=PRODUCTSET_ID_TEST,
                product_set=product_set,
                update_mask=None,
                project_id=PROJECT_ID_TEST,
                retry=DEFAULT,
                timeout=None,
                metadata=(),
            )
        err = ctx.value
        assert err
        assert ERR_DIFF_NAMES.format(
            explicit_name=explicit_ps_name,
            constructed_name=template_ps_name,
            label="ProductSet",
            id_label="productset_id",
        ) in str(err)
        update_product_set_method.assert_not_called()

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_delete_productset(self, get_conn):
        # Given
        delete_product_set_method = get_conn.return_value.delete_product_set
        delete_product_set_method.return_value = None
        name = ProductSearchClient.product_set_path(PROJECT_ID_TEST, LOC_ID_TEST, PRODUCTSET_ID_TEST)
        # When
        response = self.hook.delete_product_set(
            location=LOC_ID_TEST, product_set_id=PRODUCTSET_ID_TEST, project_id=PROJECT_ID_TEST
        )
        # Then
        assert response is None
        delete_product_set_method.assert_called_once_with(name=name, retry=DEFAULT, timeout=None, metadata=())

    @mock.patch(
        "airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn",
        **{"return_value.create_reference_image.return_value": REFERENCE_IMAGE_TEST},
    )
    def test_create_reference_image_explicit_id(self, get_conn):
        # Given
        create_reference_image_method = get_conn.return_value.create_reference_image

        # When
        result = self.hook.create_reference_image(
            project_id=PROJECT_ID_TEST,
            location=LOC_ID_TEST,
            product_id=PRODUCT_ID_TEST,
            reference_image=REFERENCE_IMAGE_WITHOUT_ID_NAME,
            reference_image_id=REFERENCE_IMAGE_ID_TEST,
        )
        # Then
        # Product ID was provided explicitly in the method call above, should be returned from the method
        assert result == REFERENCE_IMAGE_ID_TEST
        create_reference_image_method.assert_called_once_with(
            parent=PRODUCT_NAME,
            reference_image=REFERENCE_IMAGE_WITHOUT_ID_NAME,
            reference_image_id=REFERENCE_IMAGE_ID_TEST,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )

    @mock.patch(
        "airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn",
        **{"return_value.create_reference_image.return_value": REFERENCE_IMAGE_TEST},
    )
    def test_create_reference_image_autogenerated_id(self, get_conn):
        # Given
        create_reference_image_method = get_conn.return_value.create_reference_image

        # When
        result = self.hook.create_reference_image(
            project_id=PROJECT_ID_TEST,
            location=LOC_ID_TEST,
            product_id=PRODUCT_ID_TEST,
            reference_image=REFERENCE_IMAGE_TEST,
            reference_image_id=REFERENCE_IMAGE_ID_TEST,
        )
        # Then
        # Product ID was provided explicitly in the method call above, should be returned from the method
        assert result == REFERENCE_IMAGE_GEN_ID_TEST
        create_reference_image_method.assert_called_once_with(
            parent=PRODUCT_NAME,
            reference_image=REFERENCE_IMAGE_TEST,
            reference_image_id=REFERENCE_IMAGE_ID_TEST,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_add_product_to_product_set(self, get_conn):
        # Given
        add_product_to_product_set_method = get_conn.return_value.add_product_to_product_set

        # When
        self.hook.add_product_to_product_set(
            product_set_id=PRODUCTSET_ID_TEST,
            product_id=PRODUCT_ID_TEST,
            location=LOC_ID_TEST,
            project_id=PROJECT_ID_TEST,
        )
        # Then
        # Product ID was provided explicitly in the method call above, should be returned from the method
        add_product_to_product_set_method.assert_called_once_with(
            name=PRODUCTSET_NAME_TEST, product=PRODUCT_NAME_TEST, retry=DEFAULT, timeout=None, metadata=()
        )

    # remove_product_from_product_set
    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_remove_product_from_product_set(self, get_conn):
        # Given
        remove_product_from_product_set_method = get_conn.return_value.remove_product_from_product_set

        # When
        self.hook.remove_product_from_product_set(
            product_set_id=PRODUCTSET_ID_TEST,
            product_id=PRODUCT_ID_TEST,
            location=LOC_ID_TEST,
            project_id=PROJECT_ID_TEST,
        )
        # Then
        # Product ID was provided explicitly in the method call above, should be returned from the method
        remove_product_from_product_set_method.assert_called_once_with(
            name=PRODUCTSET_NAME_TEST, product=PRODUCT_NAME_TEST, retry=DEFAULT, timeout=None, metadata=()
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_annotate_image(self, annotator_client_mock):
        # Given
        annotate_image_method = annotator_client_mock.annotate_image

        # When
        self.hook.annotate_image(request=ANNOTATE_IMAGE_REQUEST)
        # Then
        # Product ID was provided explicitly in the method call above, should be returned from the method
        annotate_image_method.assert_called_once_with(
            request=ANNOTATE_IMAGE_REQUEST, retry=DEFAULT, timeout=None
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_batch_annotate_images(self, annotator_client_mock):
        # Given
        batch_annotate_images_method = annotator_client_mock.batch_annotate_images

        # When
        self.hook.batch_annotate_images(requests=BATCH_ANNOTATE_IMAGE_REQUEST)
        # Then
        # Product ID was provided explicitly in the method call above, should be returned from the method
        batch_annotate_images_method.assert_called_once_with(
            requests=list(map(AnnotateImageRequest, BATCH_ANNOTATE_IMAGE_REQUEST)),
            retry=DEFAULT,
            timeout=None,
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_create_product_explicit_id(self, get_conn):
        # Given
        create_product_method = get_conn.return_value.create_product
        create_product_method.return_value = None
        parent = f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}"
        product = Product()
        # When
        result = self.hook.create_product(
            location=LOC_ID_TEST, product_id=PRODUCT_ID_TEST, product=product, project_id=PROJECT_ID_TEST
        )
        # Then
        # Product ID was provided explicitly in the method call above, should be returned from the method
        assert result == PRODUCT_ID_TEST
        create_product_method.assert_called_once_with(
            parent=parent,
            product=product,
            product_id=PRODUCT_ID_TEST,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_create_product_autogenerated_id(self, get_conn):
        # Given
        autogenerated_id = "autogen-p-id"
        response_product = Product(
            name=ProductSearchClient.product_path(PROJECT_ID_TEST, LOC_ID_TEST, autogenerated_id)
        )
        create_product_method = get_conn.return_value.create_product
        create_product_method.return_value = response_product
        parent = f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}"
        product = Product()
        # When
        result = self.hook.create_product(
            location=LOC_ID_TEST, product_id=None, product=product, project_id=PROJECT_ID_TEST
        )
        # Then
        # Product ID was not provided in the method call above. Should be extracted from the API response
        # and returned.
        assert result == autogenerated_id
        create_product_method.assert_called_once_with(
            parent=parent, product=product, product_id=None, retry=DEFAULT, timeout=None, metadata=()
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_create_product_autogenerated_id_wrong_name_in_response(self, get_conn):
        # Given
        wrong_name = "wrong_name_not_a_correct_path"
        response_product = Product(name=wrong_name)
        create_product_method = get_conn.return_value.create_product
        create_product_method.return_value = response_product
        parent = f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}"
        product = Product()
        # When
        with pytest.raises(AirflowException) as ctx:
            self.hook.create_product(
                location=LOC_ID_TEST, product_id=None, product=product, project_id=PROJECT_ID_TEST
            )
        # Then
        # API response was wrong (wrong name format) and thus ProductSet ID extraction should fail.
        err = ctx.value
        assert "Unable to get id from name" in str(err)
        create_product_method.assert_called_once_with(
            parent=parent, product=product, product_id=None, retry=DEFAULT, timeout=None, metadata=()
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_create_product_autogenerated_id_wrong_api_response(self, get_conn):
        # Given
        response_product = None
        create_product_method = get_conn.return_value.create_product
        create_product_method.return_value = response_product
        parent = f"projects/{PROJECT_ID_TEST}/locations/{LOC_ID_TEST}"
        product = Product()
        # When
        with pytest.raises(AirflowException) as ctx:
            self.hook.create_product(
                location=LOC_ID_TEST, product_id=None, product=product, project_id=PROJECT_ID_TEST
            )
        # Then
        # API response was wrong (None) and thus ProductSet ID extraction should fail.
        err = ctx.value
        assert "Unable to get name from response..." in str(err)
        create_product_method.assert_called_once_with(
            parent=parent, product=product, product_id=None, retry=DEFAULT, timeout=None, metadata=()
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_update_product_no_explicit_name(self, get_conn):
        # Given
        product = Product()
        update_product_method = get_conn.return_value.update_product
        update_product_method.return_value = product
        product_name = ProductSearchClient.product_path(PROJECT_ID_TEST, LOC_ID_TEST, PRODUCT_ID_TEST)
        # When
        result = self.hook.update_product(
            location=LOC_ID_TEST,
            product_id=PRODUCT_ID_TEST,
            product=product,
            update_mask=None,
            project_id=PROJECT_ID_TEST,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )
        # Then
        assert result == MessageToDict(product._pb)
        update_product_method.assert_called_once_with(
            product=Product(name=product_name), metadata=(), retry=DEFAULT, timeout=None, update_mask=None
        )

    @pytest.mark.parametrize("location, product_id", LOCATION_PRODUCT_ID_TEST_PARAMS)
    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_update_product_no_explicit_name_and_missing_params_for_constructed_name(
        self, get_conn, location, product_id
    ):
        # Given
        update_product_method = get_conn.return_value.update_product
        update_product_method.return_value = None
        product = Product()
        # When
        with pytest.raises(AirflowException) as ctx:
            self.hook.update_product(
                location=location,
                product_id=product_id,
                product=product,
                update_mask=None,
                project_id=PROJECT_ID_TEST,
                retry=DEFAULT,
                timeout=None,
                metadata=(),
            )
        err = ctx.value
        assert err
        assert ERR_UNABLE_TO_CREATE.format(label="Product", id_label="product_id") in str(err)
        update_product_method.assert_not_called()

    @pytest.mark.parametrize("location, product_id", LOCATION_PRODUCT_ID_TEST_PARAMS)
    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_update_product_explicit_name_missing_params_for_constructed_name(
        self, get_conn, location, product_id
    ):
        # Given
        explicit_p_name = ProductSearchClient.product_path(
            PROJECT_ID_TEST_2, LOC_ID_TEST_2, PRODUCT_ID_TEST_2
        )
        product = Product(name=explicit_p_name)
        update_product_method = get_conn.return_value.update_product
        update_product_method.return_value = product
        # When
        result = self.hook.update_product(
            location=location,
            product_id=product_id,
            product=product,
            update_mask=None,
            project_id=PROJECT_ID_TEST,
            retry=DEFAULT,
            timeout=None,
            metadata=(),
        )
        # Then
        assert result == MessageToDict(product._pb)
        update_product_method.assert_called_once_with(
            product=Product(name=explicit_p_name), metadata=(), retry=DEFAULT, timeout=None, update_mask=None
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_update_product_explicit_name_different_from_constructed(self, get_conn):
        # Given
        update_product_method = get_conn.return_value.update_product
        update_product_method.return_value = None
        explicit_p_name = ProductSearchClient.product_path(
            PROJECT_ID_TEST_2, LOC_ID_TEST_2, PRODUCT_ID_TEST_2
        )
        product = Product(name=explicit_p_name)
        template_p_name = ProductSearchClient.product_path(PROJECT_ID_TEST, LOC_ID_TEST, PRODUCT_ID_TEST)
        # When
        # Location and product_id are passed in addition to a Product with an explicit name,
        # but both names differ (constructed != explicit).
        # Should throw AirflowException in this case.
        with pytest.raises(AirflowException) as ctx:
            self.hook.update_product(
                location=LOC_ID_TEST,
                product_id=PRODUCT_ID_TEST,
                product=product,
                update_mask=None,
                project_id=PROJECT_ID_TEST,
                retry=DEFAULT,
                timeout=None,
                metadata=(),
            )
        err = ctx.value
        assert err
        assert ERR_DIFF_NAMES.format(
            explicit_name=explicit_p_name,
            constructed_name=template_p_name,
            label="Product",
            id_label="product_id",
        ) in str(err)
        update_product_method.assert_not_called()

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.get_conn")
    def test_delete_product(self, get_conn):
        # Given
        delete_product_method = get_conn.return_value.delete_product
        delete_product_method.return_value = None
        name = ProductSearchClient.product_path(PROJECT_ID_TEST, LOC_ID_TEST, PRODUCT_ID_TEST)
        # When
        response = self.hook.delete_product(
            location=LOC_ID_TEST, product_id=PRODUCT_ID_TEST, project_id=PROJECT_ID_TEST
        )
        # Then
        assert response is None
        delete_product_method.assert_called_once_with(name=name, retry=DEFAULT, timeout=None, metadata=())

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_detect_text(self, annotator_client_mock):
        # Given
        detect_text_method = annotator_client_mock.text_detection
        detect_text_method.return_value = AnnotateImageResponse(
            text_annotations=[EntityAnnotation(description="test", score=0.5)]
        )

        # When
        self.hook.text_detection(image=DETECT_TEST_IMAGE)

        # Then
        detect_text_method.assert_called_once_with(
            image=DETECT_TEST_IMAGE, max_results=None, retry=DEFAULT, timeout=None
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_detect_text_with_additional_properties(self, annotator_client_mock):
        # Given
        detect_text_method = annotator_client_mock.text_detection
        detect_text_method.return_value = AnnotateImageResponse(
            text_annotations=[EntityAnnotation(description="test", score=0.5)]
        )

        # When
        self.hook.text_detection(
            image=DETECT_TEST_IMAGE, additional_properties={"prop1": "test1", "prop2": "test2"}
        )

        # Then
        detect_text_method.assert_called_once_with(
            image=DETECT_TEST_IMAGE,
            max_results=None,
            retry=DEFAULT,
            timeout=None,
            prop1="test1",
            prop2="test2",
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_detect_text_with_error_response(self, annotator_client_mock):
        # Given
        detect_text_method = annotator_client_mock.text_detection
        detect_text_method.return_value = AnnotateImageResponse(
            error={"code": 3, "message": "test error message"}
        )

        # When
        with pytest.raises(AirflowException) as ctx:
            self.hook.text_detection(image=DETECT_TEST_IMAGE)

        err = ctx.value
        assert "test error message" in str(err)

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_document_text_detection(self, annotator_client_mock):
        # Given
        document_text_detection_method = annotator_client_mock.document_text_detection
        document_text_detection_method.return_value = AnnotateImageResponse(
            text_annotations=[EntityAnnotation(description="test", score=0.5)]
        )

        # When
        self.hook.document_text_detection(image=DETECT_TEST_IMAGE)

        # Then
        document_text_detection_method.assert_called_once_with(
            image=DETECT_TEST_IMAGE, max_results=None, retry=DEFAULT, timeout=None
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_document_text_detection_with_additional_properties(self, annotator_client_mock):
        # Given
        document_text_detection_method = annotator_client_mock.document_text_detection
        document_text_detection_method.return_value = AnnotateImageResponse(
            text_annotations=[EntityAnnotation(description="test", score=0.5)]
        )

        # When
        self.hook.document_text_detection(
            image=DETECT_TEST_IMAGE, additional_properties={"prop1": "test1", "prop2": "test2"}
        )

        # Then
        document_text_detection_method.assert_called_once_with(
            image=DETECT_TEST_IMAGE,
            max_results=None,
            retry=DEFAULT,
            timeout=None,
            prop1="test1",
            prop2="test2",
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_detect_document_text_with_error_response(self, annotator_client_mock):
        # Given
        detect_text_method = annotator_client_mock.document_text_detection
        detect_text_method.return_value = AnnotateImageResponse(
            error={"code": 3, "message": "test error message"}
        )

        # When
        with pytest.raises(AirflowException) as ctx:
            self.hook.document_text_detection(image=DETECT_TEST_IMAGE)

        err = ctx.value
        assert "test error message" in str(err)

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_label_detection(self, annotator_client_mock):
        # Given
        label_detection_method = annotator_client_mock.label_detection
        label_detection_method.return_value = AnnotateImageResponse(
            label_annotations=[EntityAnnotation(description="test", score=0.5)]
        )

        # When
        self.hook.label_detection(image=DETECT_TEST_IMAGE)

        # Then
        label_detection_method.assert_called_once_with(
            image=DETECT_TEST_IMAGE, max_results=None, retry=DEFAULT, timeout=None
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_label_detection_with_additional_properties(self, annotator_client_mock):
        # Given
        label_detection_method = annotator_client_mock.label_detection
        label_detection_method.return_value = AnnotateImageResponse(
            label_annotations=[EntityAnnotation(description="test", score=0.5)]
        )

        # When
        self.hook.label_detection(
            image=DETECT_TEST_IMAGE, additional_properties={"prop1": "test1", "prop2": "test2"}
        )

        # Then
        label_detection_method.assert_called_once_with(
            image=DETECT_TEST_IMAGE,
            max_results=None,
            retry=DEFAULT,
            timeout=None,
            prop1="test1",
            prop2="test2",
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_label_detection_with_error_response(self, annotator_client_mock):
        # Given
        detect_text_method = annotator_client_mock.label_detection
        detect_text_method.return_value = AnnotateImageResponse(
            error={"code": 3, "message": "test error message"}
        )

        # When
        with pytest.raises(AirflowException) as ctx:
            self.hook.label_detection(image=DETECT_TEST_IMAGE)

        err = ctx.value
        assert "test error message" in str(err)

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_safe_search_detection(self, annotator_client_mock):
        # Given
        safe_search_detection_method = annotator_client_mock.safe_search_detection
        safe_search_detection_method.return_value = AnnotateImageResponse(
            safe_search_annotation=SafeSearchAnnotation(
                adult="VERY_UNLIKELY",
                spoof="VERY_UNLIKELY",
                medical="VERY_UNLIKELY",
                violence="VERY_UNLIKELY",
                racy="VERY_UNLIKELY",
            )
        )

        # When
        self.hook.safe_search_detection(image=DETECT_TEST_IMAGE)

        # Then
        safe_search_detection_method.assert_called_once_with(
            image=DETECT_TEST_IMAGE, max_results=None, retry=DEFAULT, timeout=None
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_safe_search_detection_with_additional_properties(self, annotator_client_mock):
        # Given
        safe_search_detection_method = annotator_client_mock.safe_search_detection
        safe_search_detection_method.return_value = AnnotateImageResponse(
            safe_search_annotation=SafeSearchAnnotation(
                adult="VERY_UNLIKELY",
                spoof="VERY_UNLIKELY",
                medical="VERY_UNLIKELY",
                violence="VERY_UNLIKELY",
                racy="VERY_UNLIKELY",
            )
        )

        # When
        self.hook.safe_search_detection(
            image=DETECT_TEST_IMAGE, additional_properties={"prop1": "test1", "prop2": "test2"}
        )

        # Then
        safe_search_detection_method.assert_called_once_with(
            image=DETECT_TEST_IMAGE,
            max_results=None,
            retry=DEFAULT,
            timeout=None,
            prop1="test1",
            prop2="test2",
        )

    @mock.patch("airflow.providers.google.cloud.hooks.vision.CloudVisionHook.annotator_client")
    def test_safe_search_detection_with_error_response(self, annotator_client_mock):
        # Given
        detect_text_method = annotator_client_mock.safe_search_detection
        detect_text_method.return_value = AnnotateImageResponse(
            error={"code": 3, "message": "test error message"}
        )

        # When
        with pytest.raises(AirflowException) as ctx:
            self.hook.safe_search_detection(image=DETECT_TEST_IMAGE)

        err = ctx.value
        assert "test error message" in str(err)
