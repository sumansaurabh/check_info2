
from pathlib import Path
import requests
import pytest

from conftest import poll_job_status, download_output, verify_image_output

class TestEndToEnd:
    def test_face_swap_with_enhancer(
        self,
        api_client: requests.Session,
        api_base_url: str,
        source_image_path: Path,
        target_image_path: Path,
        cleanup_outputs: list,
        performance_tracker
    ):
        """
        End-to-end test for face swapping with face enhancer.
        """
        print("\n" + "="*60)
        print("END-TO-END FACE SWAP AND ENHANCEMENT TEST")
        print("="*60)

        # Step 1: Submit processing job
        print("\n[1/4] Submitting face swap job...")
        performance_tracker.start("total_workflow")
        performance_tracker.start("job_submission")

        with open(source_image_path, 'rb') as source_file, \
             open(target_image_path, 'rb') as target_file:

            files = {
                'source': ('source.jpg', source_file, 'image/jpeg'),
                'target': ('target.jpg', target_file, 'image/jpeg')
            }

            data = {
                'processors': '["face_swapper", "face_enhancer"]',
                'execution_providers': '["cuda"]',
                'execution_thread_count': '32',
                'face_detector_model': 'yoloface_8n',
                'face_detector_score': '0.5',
                'face_swapper_model': 'hyperswap_1a_256',
                'face_enhancer_model': 'gfpgan_1.4',
                'face_enhancer_blend': '80',
                'output_image_scale': '100'
            }

            response = api_client.post(
                f"{api_base_url}/process/image",
                files=files,
                data=data,
                timeout=30
            )

        submission_time = performance_tracker.end("job_submission")

        # Verify job was accepted
        assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
        job_response = response.json()

        assert "job_id" in job_response
        assert "status" in job_response
        assert job_response["status"] == "queued"

        job_id = job_response["job_id"]
        print(f"  ✓ Job submitted: {job_id}")
        print(f"  ⏱ Submission time: {submission_time:.3f}s")

        # Step 2: Poll for completion
        print(f"\n[2/4] Polling job status (timeout: 120s)...")
        performance_tracker.start("job_processing")

        try:
            final_status = poll_job_status(api_client, api_base_url, job_id, timeout=120)
        except TimeoutError as e:
            pytest.fail(f"Job processing timeout: {e}")

        processing_time = performance_tracker.end("job_processing")

        # Verify completion
        assert final_status["status"] == "completed", \
            f"Job failed: {final_status.get('error', 'Unknown error')}"
        assert "output_path" in final_status
        assert final_status["output_path"] is not None

        print(f"  ✓ Job completed successfully")
        print(f"  ⏱ Processing time: {processing_time:.2f}s")
        print(f"  📁 Output path: {final_status['output_path']}")

        # Step 3: Download output
        print(f"\n[3/4] Downloading output image...")
        performance_tracker.start("download")

        output_filename = Path(final_status["output_path"]).name
        
        # Save to a dedicated output folder for manual verification
        test_output_dir = Path.cwd() / "test_outputs"
        test_output_dir.mkdir(exist_ok=True)
        local_output = test_output_dir / f"result_{output_filename}"

        # Also track for cleanup
        cleanup_outputs.append(str(local_output))

        downloaded_path = download_output(
            api_client,
            api_base_url,
            final_status["output_path"],
            local_output,
            cleanup=False
        )

        download_time = performance_tracker.end("download")

        print(f"  ✓ Downloaded to: {downloaded_path}")
        print(f"  ⏱ Download time: {download_time:.3f}s")
        print(f"  📊 File size: {downloaded_path.stat().st_size / 1024:.1f} KB")
        print(f"\n  🖼️  VIEW YOUR RESULT: open {downloaded_path}")

        # Step 4: Verify output
        print(f"\n[4/4] Verifying output image...")
        verify_image_output(downloaded_path, min_size_kb=10)
        print(f"  ✓ Output image is valid")

        # Performance summary
        total_time = performance_tracker.end("total_workflow")
        print(f"\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)
        print(f"  Job submission:  {submission_time:.3f}s")
        print(f"  Job processing:  {processing_time:.2f}s")
        print(f"  File download:   {download_time:.3f}s")
        print(f"  Total workflow:  {total_time:.2f}s")
        print("="*60)

        # Performance assertions
        assert submission_time < 5.0, "Job submission too slow"
        assert processing_time < 120.0, "Processing took too long"
        assert download_time < 10.0, "Download too slow"
