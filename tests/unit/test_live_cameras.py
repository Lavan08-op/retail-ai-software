from config.live_cameras import load_live_camera_urls


def test_live_camera_urls_default_to_four_phone_streams():
    urls = load_live_camera_urls({})

    assert urls == {
        "entry-cam": "rtsp://127.0.0.1:8554/entry-cam",
        "queue-cam-1": "rtsp://127.0.0.1:8554/queue-cam-1",
        "queue-cam-2": "rtsp://127.0.0.1:8554/queue-cam-2",
        "shelf-cam-1": "rtsp://127.0.0.1:8554/shelf-cam-1",
    }


def test_live_camera_urls_allow_direct_phone_overrides():
    urls = load_live_camera_urls(
        {
            "STORESENSE_CAMERA_IDS": "entry-cam, queue-cam-1",
            "STORESENSE_RTSP_BASE_URL": "rtsp://server:8554",
            "STORESENSE_RTSP_URL_ENTRY_CAM": "http://192.168.1.51:8080/video",
        }
    )

    assert urls["entry-cam"] == "http://192.168.1.51:8080/video"
    assert urls["queue-cam-1"] == "rtsp://server:8554/queue-cam-1"
